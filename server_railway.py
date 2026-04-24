#!/usr/bin/env python3
"""
Simple Authentication Server - Railway Compatible
Works with both SQLite (local) and PostgreSQL (production)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import secrets
import time
import os

app = Flask(__name__)
CORS(app)

# Auto-detect database type
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///auth.db')
USE_POSTGRES = DATABASE_URL.startswith('postgres')

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    # Fix Railway's postgres:// to postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    print(f"[+] Using PostgreSQL")
else:
    import sqlite3
    DATABASE = 'auth.db'
    print(f"[+] Using SQLite: {DATABASE}")

# ==================== Database Functions ====================

def get_db_connection():
    """Get database connection (SQLite or PostgreSQL)"""
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        conn = sqlite3.connect(DATABASE, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        # PostgreSQL schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                id TEXT PRIMARY KEY,
                license_key TEXT UNIQUE NOT NULL,
                hwid TEXT DEFAULT '',
                username TEXT DEFAULT 'User',
                expiry BIGINT NOT NULL,
                duration INTEGER NOT NULL,
                status INTEGER DEFAULT 0,
                created_at BIGINT NOT NULL,
                last_used BIGINT DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                event_type TEXT NOT NULL,
                license_key TEXT,
                ip_address TEXT,
                details TEXT,
                created_at BIGINT NOT NULL
            )
        ''')
    else:
        # SQLite schema
        cursor.execute('PRAGMA journal_mode=WAL')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                id TEXT PRIMARY KEY,
                license_key TEXT UNIQUE NOT NULL,
                hwid TEXT DEFAULT '',
                username TEXT DEFAULT 'User',
                expiry INTEGER NOT NULL,
                duration INTEGER NOT NULL,
                status INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL,
                last_used INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                license_key TEXT,
                ip_address TEXT,
                details TEXT,
                created_at INTEGER NOT NULL
            )
        ''')
    
    conn.commit()
    conn.close()
    print("[+] Database initialized")

def log_audit(event_type, license_key='', ip_address='', details=''):
    """Log audit event"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (event_type, license_key, ip_address, details, created_at)
            VALUES (%s, %s, %s, %s, %s)
        ''' if USE_POSTGRES else '''
            INSERT INTO audit_logs (event_type, license_key, ip_address, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (event_type, license_key, ip_address, details, int(time.time())))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Audit log failed: {e}")

# ==================== API Endpoints ====================

@app.route('/api/client/authenticate', methods=['POST'])
def authenticate():
    data = request.get_json()
    
    if not data or 'license_key' not in data or 'hwid' not in data:
        return jsonify({'success': False, 'message': 'Missing fields'}), 400
    
    license_key = data['license_key']
    hwid = data['hwid']
    ip = request.remote_addr
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get license
        cursor.execute('SELECT * FROM licenses WHERE license_key = %s' if USE_POSTGRES else 
                      'SELECT * FROM licenses WHERE license_key = ?', (license_key,))
        license = cursor.fetchone()
        
        if not license:
            log_audit('auth_failed', license_key, ip, 'Invalid license')
            return jsonify({'success': False, 'message': 'Invalid license key'}), 401
        
        # Check expiry
        now = int(time.time())
        if license['expiry'] < now and license['expiry'] != 9999999999:
            log_audit('auth_expired', license_key, ip, 'License expired')
            return jsonify({'success': False, 'message': 'License expired'}), 403
        
        # Check HWID
        if license['hwid'] and license['hwid'] != hwid:
            log_audit('auth_hwid_mismatch', license_key, ip, f'HWID: {hwid}')
            return jsonify({'success': False, 'message': 'HWID mismatch. Contact admin to reset.'}), 403
        
        # Bind HWID if first use
        if not license['hwid']:
            cursor.execute('UPDATE licenses SET hwid = %s WHERE license_key = %s' if USE_POSTGRES else
                          'UPDATE licenses SET hwid = ? WHERE license_key = ?', (hwid, license_key))
            conn.commit()
            log_audit('hwid_bound', license_key, ip, f'HWID: {hwid}')
        
        # Update last used
        cursor.execute('UPDATE licenses SET last_used = %s WHERE license_key = %s' if USE_POSTGRES else
                      'UPDATE licenses SET last_used = ? WHERE license_key = ?', (now, license_key))
        conn.commit()
        
        log_audit('auth_success', license_key, ip, 'Login successful')
        
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'username': license['username'],
            'expires_at': license['expiry']
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Authentication error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/licenses', methods=['GET'])
def get_licenses():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM licenses ORDER BY created_at DESC')
        licenses = cursor.fetchall()
        
        result = []
        for lic in licenses:
            result.append({
                'id': lic['id'],
                'license_key': lic['license_key'],
                'username': lic['username'],
                'hwid': lic['hwid'],
                'expiry': lic['expiry'],
                'duration': lic['duration'],
                'status': lic['status'],
                'created_at': lic['created_at'],
                'last_used': lic['last_used']
            })
        
        return jsonify({'licenses': result}), 200
    except Exception as e:
        print(f"[ERROR] Get licenses error: {e}")
        return jsonify({'licenses': []}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/license', methods=['POST'])
def create_license():
    data = request.get_json()
    
    if not data or 'duration' not in data:
        return jsonify({'success': False, 'message': 'Missing duration'}), 400
    
    duration = int(data['duration'])
    username = data.get('username', 'User')
    
    # Generate license key
    license_key = secrets.token_hex(16).upper()
    license_key = f"{license_key[:8]}-{license_key[8:16]}-{license_key[16:24]}-{license_key[24:32]}"
    
    license_id = secrets.token_hex(16)
    now = int(time.time())
    expiry = now + duration
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO licenses (id, license_key, username, expiry, duration, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''' if USE_POSTGRES else '''
            INSERT INTO licenses (id, license_key, username, expiry, duration, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (license_id, license_key, username, expiry, duration, now))
        conn.commit()
        
        return jsonify({
            'success': True,
            'license_key': license_key,
            'expiry': expiry
        }), 200
    except Exception as e:
        print(f"[ERROR] Create license error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/license/<license_id>/hwid', methods=['DELETE'])
def reset_hwid(license_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE licenses SET hwid = %s WHERE id = %s' if USE_POSTGRES else
                      'UPDATE licenses SET hwid = ? WHERE id = ?', ('', license_id))
        conn.commit()
        
        log_audit('hwid_reset', '', request.remote_addr, f'License ID: {license_id}')
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"[ERROR] Reset HWID error: {e}")
        return jsonify({'success': False}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/license/<license_id>/time', methods=['POST'])
def add_time(license_id):
    data = request.get_json()
    
    if not data or 'seconds' not in data:
        return jsonify({'success': False}), 400
    
    seconds = int(data['seconds'])
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE licenses SET expiry = expiry + %s WHERE id = %s' if USE_POSTGRES else
                      'UPDATE licenses SET expiry = expiry + ? WHERE id = ?', (seconds, license_id))
        conn.commit()
        
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"[ERROR] Add time error: {e}")
        return jsonify({'success': False}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/license/<license_id>', methods=['DELETE'])
def delete_license(license_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM licenses WHERE id = %s' if USE_POSTGRES else
                      'DELETE FROM licenses WHERE id = ?', (license_id,))
        conn.commit()
        
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"[ERROR] Delete license error: {e}")
        return jsonify({'success': False}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/logs', methods=['GET'])
def get_logs():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100')
        logs = cursor.fetchall()
        
        result = []
        for log in logs:
            result.append({
                'id': log['id'],
                'event_type': log['event_type'],
                'license_key': log['license_key'],
                'ip_address': log['ip_address'],
                'details': log['details'],
                'created_at': log['created_at']
            })
        
        return jsonify({'logs': result}), 200
    except Exception as e:
        print(f"[ERROR] Get logs error: {e}")
        return jsonify({'logs': []}), 500
    finally:
        if conn:
            conn.close()

@app.route('/', methods=['GET'])
def index():
    return '''
    <html>
    <head><title>Simple Auth Server</title></head>
    <body style="font-family: monospace; background: #0a0a0a; color: #00ff88; padding: 40px;">
        <h1>🔐 Simple Auth Server</h1>
        <p>Server is running on Railway!</p>
        <p>Database: ''' + ('PostgreSQL' if USE_POSTGRES else 'SQLite') + '''</p>
        <h2>API Endpoints:</h2>
        <ul>
            <li>POST /api/client/authenticate - Client authentication</li>
            <li>GET /api/admin/licenses - List all licenses</li>
            <li>POST /api/admin/license - Create new license</li>
        </ul>
    </body>
    </html>
    '''

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'database': 'PostgreSQL' if USE_POSTGRES else 'SQLite'}), 200

# ==================== Main ====================

if __name__ == '__main__':
    print("=" * 60)
    print("Simple Authentication Server - Railway Compatible")
    print("=" * 60)
    
    init_db()
    
    port = int(os.environ.get('PORT', 8080))
    print(f"\n[+] Server starting on port {port}")
    print(f"[+] Database: {'PostgreSQL' if USE_POSTGRES else 'SQLite'}")
    print(f"[+] Press Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
