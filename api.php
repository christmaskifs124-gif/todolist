<?php
// Aether Cheats - Killswitch API Backend
// Simple PHP backend for killswitch control

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST');
header('Access-Control-Allow-Headers: Content-Type');

// Configuration
define('STATUS_FILE', 'status.txt');
define('LOG_FILE', 'activity.log');
define('STATS_FILE', 'stats.json');
define('ADMIN_PASSWORD', 'your_secure_password_here'); // Change this!

// Get action
$action = isset($_GET['action']) ? $_GET['action'] : '';

// Handle requests
switch ($action) {
    case 'getStatus':
        getStatus();
        break;
    
    case 'setStatus':
        setStatus();
        break;
    
    case 'getStats':
        getStats();
        break;
    
    case 'getLog':
        getLog();
        break;
    
    default:
        echo json_encode(['success' => false, 'error' => 'Invalid action']);
        break;
}

// Get current status
function getStatus() {
    if (!file_exists(STATUS_FILE)) {
        file_put_contents(STATUS_FILE, '1'); // Default: enabled
    }
    
    $status = trim(file_get_contents(STATUS_FILE));
    
    // Increment check counter
    incrementCheckCounter();
    
    echo json_encode([
        'success' => true,
        'status' => $status
    ]);
}

// Set status (enable/disable killswitch)
function setStatus() {
    // Get POST data
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!isset($input['status'])) {
        echo json_encode(['success' => false, 'error' => 'Missing status parameter']);
        return;
    }
    
    $newStatus = $input['status'];
    
    // Validate status
    if ($newStatus !== '0' && $newStatus !== '1') {
        echo json_encode(['success' => false, 'error' => 'Invalid status value']);
        return;
    }
    
    // Write status file
    file_put_contents(STATUS_FILE, $newStatus);
    
    // Log the change
    $timestamp = date('Y-m-d H:i:s');
    $message = $newStatus === '1' ? 'Cheat ENABLED' : 'Killswitch ACTIVATED';
    $logEntry = "[{$timestamp}] {$message}\n";
    file_put_contents(LOG_FILE, $logEntry, FILE_APPEND);
    
    // Update stats
    updateLastChange();
    
    echo json_encode([
        'success' => true,
        'status' => $newStatus
    ]);
}

// Get statistics
function getStats() {
    $stats = loadStats();
    
    // Calculate uptime percentage (simplified)
    $uptime = '99.9%'; // You can implement real uptime tracking
    
    echo json_encode([
        'success' => true,
        'stats' => [
            'checksToday' => $stats['checksToday'],
            'lastChange' => $stats['lastChange'],
            'uptime' => $uptime
        ]
    ]);
}

// Get activity log
function getLog() {
    if (!file_exists(LOG_FILE)) {
        echo json_encode(['success' => true, 'log' => []]);
        return;
    }
    
    $lines = file(LOG_FILE, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    $log = [];
    
    // Get last 50 entries
    $lines = array_slice($lines, -50);
    $lines = array_reverse($lines);
    
    foreach ($lines as $line) {
        // Parse log entry: [2024-01-01 12:00:00] Message
        if (preg_match('/\[(.*?)\] (.*)/', $line, $matches)) {
            $log[] = [
                'timestamp' => $matches[1],
                'message' => $matches[2],
                'type' => strpos($matches[2], 'ENABLED') !== false ? 'enable' : 'disable'
            ];
        }
    }
    
    echo json_encode([
        'success' => true,
        'log' => $log
    ]);
}

// Helper: Load stats
function loadStats() {
    if (!file_exists(STATS_FILE)) {
        $defaultStats = [
            'checksToday' => 0,
            'lastCheckDate' => date('Y-m-d'),
            'lastChange' => 'Never'
        ];
        file_put_contents(STATS_FILE, json_encode($defaultStats));
        return $defaultStats;
    }
    
    return json_decode(file_get_contents(STATS_FILE), true);
}

// Helper: Save stats
function saveStats($stats) {
    file_put_contents(STATS_FILE, json_encode($stats));
}

// Helper: Increment check counter
function incrementCheckCounter() {
    $stats = loadStats();
    
    // Reset counter if new day
    $today = date('Y-m-d');
    if ($stats['lastCheckDate'] !== $today) {
        $stats['checksToday'] = 0;
        $stats['lastCheckDate'] = $today;
    }
    
    $stats['checksToday']++;
    saveStats($stats);
}

// Helper: Update last change timestamp
function updateLastChange() {
    $stats = loadStats();
    $stats['lastChange'] = date('Y-m-d H:i:s');
    saveStats($stats);
}
?>
