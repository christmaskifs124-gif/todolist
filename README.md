# Aether Cheats - Killswitch Dashboard

A complete killswitch control panel for your cheat with a dark, modern UI matching your cheat's aesthetic.

## Features

- ✅ Real-time killswitch control (Enable/Disable cheat)
- 📊 Live statistics (checks today, last change, uptime)
- 📝 Activity log (tracks all status changes)
- 🎨 Dark theme matching your cheat's UI
- 🔄 Auto-refresh every 5 seconds
- 📱 Responsive design (works on mobile)

## Setup Instructions

### 1. Upload Files to Your Web Server

Upload these files to your web hosting:
```
index.html
style.css
script.js
api.php
```

### 2. Configure the Backend

Edit `api.php` and change the admin password:
```php
define('ADMIN_PASSWORD', 'your_secure_password_here'); // Change this!
```

### 3. Set Permissions

Make sure the PHP script can write files:
```bash
chmod 755 api.php
chmod 666 status.txt (will be created automatically)
chmod 666 activity.log (will be created automatically)
chmod 666 stats.json (will be created automatically)
```

### 4. Update Your Cheat

In `entry.cpp`, update the killswitch URL:
```cpp
const char* killswitch_url = "https://yourwebsite.com/status.txt";
```

Replace `yourwebsite.com` with your actual domain.

## How It Works

### Status File (`status.txt`)
- Contains a single character: `1` or `0`
- `1` = Cheat enabled (users can run it)
- `0` = Killswitch active (cheat exits with error)

### Dashboard Controls
- **Enable Cheat** button: Sets status to `1`
- **Disable Cheat** button: Sets status to `0` (activates killswitch)

### User Experience
When killswitch is active (`0`), users see:
```
Service Unavailable
This software is currently unavailable.
Please check discord for updates.
```

## Files Created Automatically

- `status.txt` - Current killswitch status (1 or 0)
- `activity.log` - Log of all status changes
- `stats.json` - Statistics data (checks, timestamps)

## Security Notes

1. **Protect the admin panel** - Add `.htaccess` password protection:
```apache
AuthType Basic
AuthName "Admin Area"
AuthUserFile /path/to/.htpasswd
Require valid-user
```

2. **Use HTTPS** - Always use SSL/TLS for the admin panel

3. **Change the password** - Update `ADMIN_PASSWORD` in `api.php`

4. **Restrict access** - Consider IP whitelisting for the admin panel

## Testing

1. Open `index.html` in your browser
2. Click "Disable Cheat" - status.txt should contain `0`
3. Click "Enable Cheat" - status.txt should contain `1`
4. Check the activity log for entries
5. Test your cheat - it should exit when killswitch is active

## Customization

### Change Colors
Edit `style.css` and modify the color variables:
```css
/* Primary color (cyan/blue) */
#00d4ff -> your color

/* Success color (green) */
#00ff88 -> your color

/* Danger color (red) */
#ff4444 -> your color
```

### Change Title
Edit `index.html`:
```html
<h1>⚡ Aether Cheats</h1>
```

### Add Authentication
The current version has no authentication. To add login:
1. Add a login page
2. Use PHP sessions
3. Check session in `api.php`

## Troubleshooting

### Status not updating
- Check file permissions (PHP needs write access)
- Check PHP error log
- Verify `api.php` is accessible

### Cheat not respecting killswitch
- Verify the URL in `entry.cpp` is correct
- Check that `status.txt` is publicly accessible
- Test the URL in a browser

### Dashboard not loading
- Check browser console for errors
- Verify all files are uploaded
- Check that `api.php` is working (visit it directly)

## Support

For issues or questions, contact your development team.

## License

Proprietary - For internal use only
