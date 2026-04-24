#!/usr/bin/env python3
"""
Simple Authentication Server - Railway Compatible
Works with both SQLite (local) and PostgreSQL (production)
"""

from flask import Flask, request, jsonify, session, redirect
from flask_cors import CORS
import secrets
import time
import os
import hashlib

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Secret key for sessions
CORS(app, supports_credentials=True)  # Enable credentials for session cookies

# Admin credentials (username: password_hash)
ADMIN_USERS = {
    'spade': hashlib.sha256('spade666'.encode()).hexdigest(),
    'andy': hashlib.sha256('andy123'.encode()).hexdigest()
}

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

# Initialize database on startup
_db_initialized = False

def ensure_db_initialized():
    """Ensure database is initialized (called before first request)"""
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True

@app.before_request
def before_request():
    """Initialize database before first request"""
    ensure_db_initialized()

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
                product TEXT DEFAULT 'fortnite',
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
                product TEXT,
                ip_address TEXT,
                details TEXT,
                created_at BIGINT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at BIGINT NOT NULL
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
                product TEXT DEFAULT 'fortnite',
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
                product TEXT,
                ip_address TEXT,
                details TEXT,
                created_at INTEGER NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
        ''')
    
    # Initialize killswitch to enabled (1)
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO settings (key, value, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO NOTHING
            ''', ('killswitch', '1', int(time.time())))
            cursor.execute('''
                INSERT INTO settings (key, value, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO NOTHING
            ''', ('killswitch_fortnite', '1', int(time.time())))
            cursor.execute('''
                INSERT INTO settings (key, value, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO NOTHING
            ''', ('killswitch_roblox', '1', int(time.time())))
        else:
            cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', ('killswitch', '1', int(time.time())))
            cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', ('killswitch_fortnite', '1', int(time.time())))
            cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', ('killswitch_roblox', '1', int(time.time())))
    except Exception as e:
        print(f"[WARNING] Killswitch init: {e}")
        pass
    
    conn.commit()
    conn.close()
    print("[+] Database initialized")

def log_audit(event_type, license_key='', ip_address='', details='', product=''):
    """Log audit event"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (event_type, license_key, product, ip_address, details, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''' if USE_POSTGRES else '''
            INSERT INTO audit_logs (event_type, license_key, product, ip_address, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (event_type, license_key, product, ip_address, details, int(time.time())))
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
    product = data.get('product', 'fortnite')  # Default to fortnite for backward compatibility
    ip = request.remote_addr
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check killswitch (global and product-specific)
        cursor.execute('SELECT value FROM settings WHERE key = %s' if USE_POSTGRES else 
                      'SELECT value FROM settings WHERE key = ?', ('killswitch',))
        killswitch_row = cursor.fetchone()
        
        cursor.execute('SELECT value FROM settings WHERE key = %s' if USE_POSTGRES else 
                      'SELECT value FROM settings WHERE key = ?', (f'killswitch_{product}',))
        product_killswitch_row = cursor.fetchone()
        
        if (killswitch_row and killswitch_row['value'] == '0') or (product_killswitch_row and product_killswitch_row['value'] == '0'):
            log_audit('auth_blocked', license_key, ip, 'Killswitch active', product)
            return jsonify({'success': False, 'message': 'Service temporarily unavailable. Please try again later.'}), 503
        
        # Get license and check product
        cursor.execute('SELECT * FROM licenses WHERE license_key = %s' if USE_POSTGRES else 
                      'SELECT * FROM licenses WHERE license_key = ?', (license_key,))
        license = cursor.fetchone()
        
        if not license:
            log_audit('auth_failed', license_key, ip, 'Invalid license', product)
            return jsonify({'success': False, 'message': 'Invalid license key'}), 401
        
        # Check if license is for the correct product
        if license['product'] != product:
            log_audit('auth_wrong_product', license_key, ip, f'License for {license["product"]}, tried to use for {product}', product)
            return jsonify({'success': False, 'message': f'This license is for {license["product"].title()} product only'}), 403
        
        # Check expiry
        now = int(time.time())
        if license['expiry'] < now and license['expiry'] != 9999999999:
            log_audit('auth_expired', license_key, ip, 'License expired', product)
            return jsonify({'success': False, 'message': 'License expired'}), 403
        
        # Check HWID
        if license['hwid'] and license['hwid'] != hwid:
            log_audit('auth_hwid_mismatch', license_key, ip, f'HWID: {hwid}', product)
            return jsonify({'success': False, 'message': 'HWID mismatch. Contact admin to reset.'}), 403
        
        # Bind HWID if first use
        if not license['hwid']:
            cursor.execute('UPDATE licenses SET hwid = %s WHERE license_key = %s' if USE_POSTGRES else
                          'UPDATE licenses SET hwid = ? WHERE license_key = ?', (hwid, license_key))
            conn.commit()
            log_audit('hwid_bound', license_key, ip, f'HWID: {hwid}', product)
        
        # Update last used
        cursor.execute('UPDATE licenses SET last_used = %s WHERE license_key = %s' if USE_POSTGRES else
                      'UPDATE licenses SET last_used = ? WHERE license_key = ?', (now, license_key))
        conn.commit()
        
        log_audit('auth_success', license_key, ip, 'Login successful', product)
        
        return jsonify({
            'success': True,
            'message': 'Authentication successful',
            'username': license['username'],
            'product': license['product'],
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
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    product_filter = request.args.get('product', 'all')
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, ensure product column exists by trying to add it
        try:
            if USE_POSTGRES:
                cursor.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS product TEXT DEFAULT 'fortnite'")
                cursor.execute("UPDATE licenses SET product = 'fortnite' WHERE product IS NULL")
            else:
                try:
                    cursor.execute("ALTER TABLE licenses ADD COLUMN product TEXT DEFAULT 'fortnite'")
                except:
                    pass
                cursor.execute("UPDATE licenses SET product = 'fortnite' WHERE product IS NULL OR product = ''")
            conn.commit()
        except Exception as e:
            print(f"[WARNING] Column migration: {e}")
        
        # Now fetch licenses
        if product_filter == 'all':
            cursor.execute('SELECT * FROM licenses ORDER BY created_at DESC')
        else:
            cursor.execute('SELECT * FROM licenses WHERE product = %s ORDER BY created_at DESC' if USE_POSTGRES else
                          'SELECT * FROM licenses WHERE product = ? ORDER BY created_at DESC', (product_filter,))
        
        licenses = cursor.fetchall()
        
        result = []
        for lic in licenses:
            # Handle both dict and tuple responses
            if USE_POSTGRES or hasattr(lic, 'keys'):
                result.append({
                    'id': lic['id'],
                    'license_key': lic['license_key'],
                    'username': lic['username'],
                    'product': lic.get('product') or 'fortnite',
                    'hwid': lic['hwid'] or '',
                    'expiry': lic['expiry'],
                    'duration': lic['duration'],
                    'status': lic.get('status', 0),
                    'created_at': lic['created_at'],
                    'last_used': lic.get('last_used', 0)
                })
            else:
                # Fallback for tuple
                result.append({
                    'id': lic[0],
                    'license_key': lic[1],
                    'username': lic[3],
                    'product': 'fortnite',
                    'hwid': lic[2] or '',
                    'expiry': lic[5],
                    'duration': lic[6],
                    'status': 0,
                    'created_at': lic[8],
                    'last_used': lic[9] if len(lic) > 9 else 0
                })
        
        print(f"[INFO] Returning {len(result)} licenses for product filter: {product_filter}")
        return jsonify({'licenses': result}), 200
        
    except Exception as e:
        print(f"[ERROR] Get licenses error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'licenses': [], 'error': str(e)}), 200  # Return 200 with empty array
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/license', methods=['POST'])
def create_license():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    
    if not data or 'duration' not in data:
        return jsonify({'success': False, 'message': 'Missing duration'}), 400
    
    duration = int(data['duration'])
    username = data.get('username', 'User')
    product = data.get('product', 'fortnite')
    
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
            INSERT INTO licenses (id, license_key, username, product, expiry, duration, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''' if USE_POSTGRES else '''
            INSERT INTO licenses (id, license_key, username, product, expiry, duration, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (license_id, license_key, username, product, expiry, duration, now))
        conn.commit()
        
        return jsonify({
            'success': True,
            'license_key': license_key,
            'product': product,
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
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
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
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
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
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized', 'success': False}), 401
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if license exists first
        cursor.execute('SELECT id FROM licenses WHERE id = %s' if USE_POSTGRES else
                      'SELECT id FROM licenses WHERE id = ?', (license_id,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"[WARNING] License {license_id} not found")
            return jsonify({'success': False, 'message': 'License not found'}), 404
        
        # Delete the license
        cursor.execute('DELETE FROM licenses WHERE id = %s' if USE_POSTGRES else
                      'DELETE FROM licenses WHERE id = ?', (license_id,))
        conn.commit()
        
        print(f"[INFO] License {license_id} deleted successfully")
        return jsonify({'success': True, 'message': 'License deleted'}), 200
        
    except Exception as e:
        print(f"[ERROR] Delete license error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/logs', methods=['GET'])
def get_logs():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
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
        <h2>Links:</h2>
        <ul>
            <li><a href="/admin" style="color: #00ff88;">Admin Dashboard</a></li>
        </ul>
        <h2>API Endpoints:</h2>
        <ul>
            <li>POST /api/client/authenticate - Client authentication</li>
            <li>GET /api/admin/licenses - List all licenses</li>
            <li>POST /api/admin/license - Create new license</li>
        </ul>
    </body>
    </html>
    '''

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if username in ADMIN_USERS and ADMIN_USERS[username] == password_hash:
        session['admin_logged_in'] = True
        session['admin_username'] = username
        return jsonify({'success': True}), 200
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({'success': True}), 200

@app.route('/admin/check', methods=['GET'])
def admin_check():
    if session.get('admin_logged_in'):
        return jsonify({'logged_in': True, 'username': session.get('admin_username')}), 200
    return jsonify({'logged_in': False}), 401

@app.route('/api/admin/killswitch', methods=['GET'])
def get_killswitch():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    product = request.args.get('product', 'global')
    key = 'killswitch' if product == 'global' else f'killswitch_{product}'
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = %s' if USE_POSTGRES else 
                      'SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        
        enabled = row['value'] == '1' if row else True
        return jsonify({'enabled': enabled, 'product': product}), 200
    except Exception as e:
        print(f"[ERROR] Get killswitch error: {e}")
        return jsonify({'enabled': True}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/killswitch', methods=['POST'])
def set_killswitch():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    enabled = data.get('enabled', True)
    product = data.get('product', 'global')
    key = 'killswitch' if product == 'global' else f'killswitch_{product}'
    value = '1' if enabled else '0'
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO settings (key, value, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
            ''', (key, value, int(time.time())))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (key, value, int(time.time())))
        
        conn.commit()
        
        status = 'enabled' if enabled else 'disabled'
        product_name = product.title() if product != 'global' else 'Global'
        log_audit('killswitch_changed', '', request.remote_addr, f'{product_name} killswitch {status} by {session.get("admin_username")}')
        
        return jsonify({'success': True, 'enabled': enabled, 'product': product}), 200
    except Exception as e:
        print(f"[ERROR] Set killswitch error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/admin', methods=['GET'])
def admin():
    with open('admin.html', 'r') as f:
        html = f.read()
    return html

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'database': 'PostgreSQL' if USE_POSTGRES else 'SQLite'}), 200

@app.route('/migrate', methods=['GET'])
def migrate():
    """Add product column to existing tables"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add product column to licenses table if it doesn't exist
        try:
            if USE_POSTGRES:
                cursor.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS product TEXT DEFAULT 'fortnite'")
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS product TEXT")
            else:
                # SQLite doesn't support IF NOT EXISTS in ALTER TABLE, so we try and catch
                try:
                    cursor.execute("ALTER TABLE licenses ADD COLUMN product TEXT DEFAULT 'fortnite'")
                except:
                    pass
                try:
                    cursor.execute("ALTER TABLE audit_logs ADD COLUMN product TEXT")
                except:
                    pass
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Database migrated successfully'}), 200
        except Exception as e:
            return jsonify({'success': False, 'message': f'Migration error: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Connection error: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

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
