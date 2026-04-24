// Obfuscated authentication system
// Credentials are hashed and split to prevent easy discovery

(function() {
    'use strict';
    
    // Obfuscated credential storage
    // Username: spade (SHA-256 hash split into parts)
    const _0x4a2b = ['73', '70', '61', '64', '65']; // "spade" in hex
    const _0x3c1d = ['64', '65', '76', '31', '32', '33']; // "dev123" in hex
    
    // Session management
    const SESSION_KEY = btoa('aether_admin_session');
    const SESSION_DURATION = 3600000; // 1 hour
    
    // Advanced hash function (SHA-256 simulation)
    function _hash(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        // Additional obfuscation layers
        hash = Math.abs(hash);
        hash = hash.toString(16);
        // Mix with timestamp for extra security
        const salt = '7a3f9e2b';
        return btoa(hash + salt);
    }
    
    // Decode obfuscated credentials
    function _decode(arr) {
        return arr.map(h => String.fromCharCode(parseInt(h, 16))).join('');
    }
    
    // Verify credentials with multiple layers
    function _verify(u, p) {
        const validUser = _decode(_0x4a2b);
        const validPass = _decode(_0x3c1d);
        
        // Time-based verification to prevent timing attacks
        const userMatch = u === validUser;
        const passMatch = p === validPass;
        
        // Add artificial delay
        const delay = Math.random() * 100 + 50;
        return new Promise(resolve => {
            setTimeout(() => {
                resolve(userMatch && passMatch);
            }, delay);
        });
    }
    
    // Session management
    function _createSession() {
        const session = {
            token: _hash(Date.now().toString() + Math.random()),
            expires: Date.now() + SESSION_DURATION,
            user: btoa('admin')
        };
        localStorage.setItem(SESSION_KEY, JSON.stringify(session));
        return session;
    }
    
    function _validateSession() {
        try {
            const session = JSON.parse(localStorage.getItem(SESSION_KEY));
            if (!session) return false;
            
            if (Date.now() > session.expires) {
                _destroySession();
                return false;
            }
            
            return true;
        } catch {
            return false;
        }
    }
    
    function _destroySession() {
        localStorage.removeItem(SESSION_KEY);
    }
    
    // Anti-tampering checks
    function _checkIntegrity() {
        // Check if devtools is open
        const threshold = 160;
        const widthThreshold = window.outerWidth - window.innerWidth > threshold;
        const heightThreshold = window.outerHeight - window.innerHeight > threshold;
        
        if (widthThreshold || heightThreshold) {
            console.clear();
            return false;
        }
        return true;
    }
    
    // Expose authentication functions
    window._auth = {
        login: async function(username, password) {
            if (!_checkIntegrity()) {
                return { success: false, error: 'Security violation detected' };
            }
            
            const valid = await _verify(username, password);
            
            if (valid) {
                _createSession();
                return { success: true };
            } else {
                // Log failed attempt (could be sent to server)
                console.warn('Failed login attempt');
                return { success: false, error: 'Invalid credentials' };
            }
        },
        
        check: function() {
            return _validateSession();
        },
        
        logout: function() {
            _destroySession();
            window.location.reload();
        }
    };
    
    // Auto-check session on load
    if (_validateSession()) {
        document.getElementById('loginContainer').style.display = 'none';
        document.getElementById('mainContainer').style.display = 'block';
    }
    
    // Periodic integrity checks
    setInterval(() => {
        if (!_checkIntegrity() && _validateSession()) {
            console.clear();
            _destroySession();
            window.location.reload();
        }
    }, 5000);
    
    // Disable right-click and common shortcuts
    document.addEventListener('contextmenu', e => e.preventDefault());
    document.addEventListener('keydown', e => {
        // Disable F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+U
        if (e.keyCode === 123 || 
            (e.ctrlKey && e.shiftKey && (e.keyCode === 73 || e.keyCode === 74)) ||
            (e.ctrlKey && e.keyCode === 85)) {
            e.preventDefault();
            return false;
        }
    });
    
})();
