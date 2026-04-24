// Configuration
const API_URL = 'api.php'; // Backend API endpoint

// State
let currentStatus = null;
let activityLog = [];

// Authentication
async function attemptLogin() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorMsg = document.getElementById('errorMessage');
    
    if (!username || !password) {
        showError('Please enter username and password');
        return false;
    }
    
    const result = await window._auth.login(username, password);
    
    if (result.success) {
        document.getElementById('loginContainer').style.display = 'none';
        document.getElementById('mainContainer').style.display = 'block';
        loadStatus();
        loadStats();
        loadActivityLog();
    } else {
        showError(result.error || 'Invalid credentials');
    }
    
    return false;
}

function logout() {
    if (confirm('Logout from admin panel?')) {
        window._auth.logout();
    }
}

function showError(message) {
    const errorMsg = document.getElementById('errorMessage');
    errorMsg.textContent = message;
    errorMsg.className = 'error-message show';
    
    setTimeout(() => {
        errorMsg.className = 'error-message';
    }, 3000);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Check if already logged in
    if (window._auth.check()) {
        document.getElementById('loginContainer').style.display = 'none';
        document.getElementById('mainContainer').style.display = 'block';
        loadStatus();
        loadStats();
        loadActivityLog();
        
        // Auto-refresh every 5 seconds
        setInterval(() => {
            loadStatus();
            loadStats();
        }, 5000);
    }
    
    // Handle Enter key on login form
    document.getElementById('password').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            attemptLogin();
        }
    });
    
    // Tab switching
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-tab');
            switchTab(tab);
        });
    });
});

// Tab switching function
function switchTab(tabName) {
    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// Load current killswitch status
async function loadStatus() {
    try {
        const response = await fetch(`${API_URL}?action=getStatus`);
        const data = await response.json();
        
        if (data.success) {
            currentStatus = data.status;
            updateStatusDisplay(data.status);
        }
    } catch (error) {
        console.error('Error loading status:', error);
        showToast('Failed to load status', true);
    }
}

// Update status display
function updateStatusDisplay(status) {
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    const statusDescription = document.getElementById('statusDescription');
    
    if (status === '1') {
        statusIndicator.className = 'status-indicator status-enabled';
        statusText.textContent = 'ENABLED';
        statusDescription.textContent = 'Cheat is currently active for all users';
    } else {
        statusIndicator.className = 'status-indicator status-disabled';
        statusText.textContent = 'DISABLED';
        statusDescription.textContent = 'Killswitch is active - cheat will not run';
    }
}

// Enable cheat
async function enableCheat() {
    if (currentStatus === '1') {
        showToast('Cheat is already enabled', false);
        return;
    }
    
    if (!confirm('Enable cheat for all users?')) return;
    
    try {
        const response = await fetch(`${API_URL}?action=setStatus`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status: '1' })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('✓ Cheat enabled successfully', false);
            loadStatus();
            loadActivityLog();
        } else {
            showToast('Failed to enable cheat', true);
        }
    } catch (error) {
        console.error('Error enabling cheat:', error);
        showToast('Error: ' + error.message, true);
    }
}

// Disable cheat (activate killswitch)
async function disableCheat() {
    if (currentStatus === '0') {
        showToast('Killswitch is already active', false);
        return;
    }
    
    if (!confirm('⚠️ ACTIVATE KILLSWITCH?\n\nThis will prevent all users from running the cheat.')) return;
    
    try {
        const response = await fetch(`${API_URL}?action=setStatus`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status: '0' })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('✓ Killswitch activated', false);
            loadStatus();
            loadActivityLog();
        } else {
            showToast('Failed to activate killswitch', true);
        }
    } catch (error) {
        console.error('Error activating killswitch:', error);
        showToast('Error: ' + error.message, true);
    }
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_URL}?action=getStats`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('checksToday').textContent = data.stats.checksToday || '0';
            document.getElementById('lastChange').textContent = data.stats.lastChange || 'Never';
            document.getElementById('uptime').textContent = data.stats.uptime || '100%';
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load activity log
async function loadActivityLog() {
    try {
        const response = await fetch(`${API_URL}?action=getLog`);
        const data = await response.json();
        
        if (data.success && data.log) {
            const logContainer = document.getElementById('activityLog');
            logContainer.innerHTML = '';
            
            if (data.log.length === 0) {
                logContainer.innerHTML = '<div class="log-entry"><span class="log-msg">No activity yet</span></div>';
                return;
            }
            
            data.log.forEach(entry => {
                const logEntry = document.createElement('div');
                logEntry.className = 'log-entry';
                
                const logTime = document.createElement('span');
                logTime.className = 'log-time';
                logTime.textContent = `[${entry.timestamp}]`;
                
                const logMessage = document.createElement('span');
                logMessage.className = `log-msg ${entry.type === 'enable' ? 'log-success' : 'log-error'}`;
                logMessage.textContent = entry.message;
                
                logEntry.appendChild(logTime);
                logEntry.appendChild(logMessage);
                logContainer.appendChild(logEntry);
            });
        }
    } catch (error) {
        console.error('Error loading activity log:', error);
    }
}

// Show toast notification
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast show' + (isError ? ' error' : ' success');
    
    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}
