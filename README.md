# Aether Cheats - Killswitch Dashboard

A complete killswitch control panel with **secure authentication** for your cheat.

## 🔐 Security Features

- ✅ Login required (username: `spade`, password: `dev123`)
- 🔒 Obfuscated credentials (not stored in plain text)
- 🛡️ Session management (1 hour timeout)
- 🚫 DevTools detection and prevention
- 🔑 Anti-tampering checks
- 📝 Failed login attempt logging

## Features

- ✅ Real-time killswitch control (Enable/Disable cheat)
- 📊 Live statistics (checks today, last change, uptime)
- 📝 Activity log (tracks all status changes)
- 🎨 Dark theme matching your cheat's UI
- 🔄 Auto-refresh every 5 seconds
- 📱 Responsive design (works on mobile)
- 🔐 **Secure login system**

## Setup Instructions

### 1. Upload Files to Your Web Server

Upload these files to your web hosting:
```
index.html
style.css
script.js
auth.js          <- NEW: Authentication system
api.php
.htaccess        <- NEW: Security configuration
```

### 2. Configure Security

The `.htaccess` file provides:
- Prevents directory listing
- Blocks access to sensitive files
- Adds security headers
- Only allows `status.txt` to be public

### 3. Set Permissions

```bash
chmod 755 api.php
chmod 644 auth.js
chmod 644 .htaccess
chmod 666 status.txt (created automatically)
chmod 666 activity.log (created automatically)
chmod 666 stats.json (created automatically)
```

### 4. Update Your Cheat

In `entry.cpp`, update the killswitch URL:
```cpp
const char* killswitch_url = "https://yourwebsite.com/status.txt";
```

## 🔑 Login Credentials

**Username:** `spade`  
**Password:** `dev123`

### Changing Credentials

To change the login credentials, edit `auth.js`:

1. Find these lines:
```javascript
const _0x4a2b = ['73', '70', '61', '64', '65']; // "spade" in hex
const _0x3c1d = ['64', '65', '76', '31', '32', '33']; // "dev123" in hex
```

2. Convert your new credentials to hex:
```javascript
// Example: username "admin" = ['61', '64', '6d', '69', '6e']
// Example: password "pass123" = ['70', '61', '73', '73', '31', '32', '33']
```

Use this tool to convert: https://www.rapidtables.com/convert/number/ascii-to-hex.html

## Security Features Explained

### 1. Obfuscated Credentials
- Credentials stored as hex arrays
- Not searchable in plain text
- Multiple encoding layers

### 2. Session Management
- 1-hour session timeout
- Secure token generation
- Auto-logout on expiry

### 3. Anti-Tampering
- DevTools detection
- Disables right-click
- Blocks F12, Ctrl+Shift+I, Ctrl+U
- Periodic integrity checks

### 4. Failed Login Protection
- Artificial delay on login attempts
- Logs failed attempts
- Prevents timing attacks

## How It Works

### Login Flow
1. User enters credentials
2. Credentials verified against obfuscated values
3. Session token created (1 hour validity)
4. Dashboard unlocked
5. Auto-logout after 1 hour or on browser close

### Status File (`status.txt`)
- Contains a single character: `1` or `0`
- `1` = Cheat enabled (users can run it)
- `0` = Killswitch active (cheat exits with error)

### Dashboard Controls
- **Enable Cheat** button: Sets status to `1`
- **Disable Cheat** button: Sets status to `0` (activates killswitch)
- **Logout** button: Ends session and returns to login

## Testing

1. Open `index.html` in your browser
2. Login with `spade` / `dev123`
3. Click "Disable Cheat" - status.txt should contain `0`
4. Click "Enable Cheat" - status.txt should contain `1`
5. Test logout - should return to login screen
6. Close browser and reopen - should require login again

## Additional Security (Recommended)

### 1. Add IP Whitelist
Edit `.htaccess`:
```apache
Order deny,allow
Deny from all
Allow from YOUR.IP.ADDRESS.HERE
```

### 2. Use HTTPS
Always use SSL/TLS certificate for the admin panel.

### 3. Change Default Credentials
Update the hex arrays in `auth.js` with your own credentials.

### 4. Add Rate Limiting
Consider adding rate limiting to prevent brute force attacks.

## Troubleshooting

### Can't login
- Check browser console for errors
- Verify credentials are correct
- Clear browser cache and cookies
- Check that `auth.js` is loading

### Session expires too quickly
Edit `auth.js` and change:
```javascript
const SESSION_DURATION = 3600000; // 1 hour in milliseconds
```

### DevTools detection too aggressive
Edit `auth.js` and adjust the threshold:
```javascript
const threshold = 160; // Increase this value
```

## Files Created Automatically

- `status.txt` - Current killswitch status (1 or 0)
- `activity.log` - Log of all status changes
- `stats.json` - Statistics data (checks, timestamps)

## Support

For issues or questions, contact your development team.

## License

Proprietary - For internal use only
