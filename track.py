from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import datetime
import os
import json
import re
import hashlib
import uuid

# Initialize Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database setup
DB_PATH = "location_tracker.db"

def init_db():
    """Initialize the SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Expanded locations table with more device information
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT,
        latitude REAL,
        longitude REAL,
        accuracy REAL,
        timestamp TEXT,
        ip_address TEXT,
        user_agent TEXT,
        browser TEXT,
        browser_version TEXT,
        operating_system TEXT,
        device_type TEXT,
        screen_resolution TEXT,
        viewport_size TEXT,
        color_depth INTEGER,
        timezone TEXT,
        language TEXT,
        cookies_enabled BOOLEAN,
        do_not_track TEXT,
        connection_type TEXT,
        battery_level REAL,
        ram TEXT,
        cpu_cores INTEGER,
        webgl_vendor TEXT,
        webgl_renderer TEXT,
        canvas_fingerprint TEXT,
        installed_plugins TEXT,
        installed_fonts TEXT,
        referrer_url TEXT,
        created_at TEXT
    )
    ''')
    
    # Enhanced devices table with additional metadata
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT UNIQUE,
        device_name TEXT,
        fingerprint_id TEXT,
        hardware_uuid TEXT,
        first_seen TEXT,
        last_seen TEXT,
        visit_count INTEGER DEFAULT 1,
        average_session_time TEXT,
        common_locations TEXT,
        metadata TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def parse_user_agent(user_agent_string):
    """Parse user agent string to extract browser, version and OS"""
    browser = "Unknown"
    browser_version = "Unknown"
    operating_system = "Unknown"
    device_type = "Desktop"
    
    # Detect mobile devices
    if any(x in user_agent_string.lower() for x in ['android', 'iphone', 'ipad', 'ipod', 'mobile']):
        device_type = "Mobile"
    elif any(x in user_agent_string.lower() for x in ['tablet']):
        device_type = "Tablet"
    
    # Detect browser
    if "Firefox/" in user_agent_string:
        browser = "Firefox"
        match = re.search(r"Firefox/([0-9\.]+)", user_agent_string)
        if match:
            browser_version = match.group(1)
    elif "Chrome/" in user_agent_string and "Chromium" not in user_agent_string:
        browser = "Chrome"
        match = re.search(r"Chrome/([0-9\.]+)", user_agent_string)
        if match:
            browser_version = match.group(1)
    elif "Safari/" in user_agent_string and "Chrome" not in user_agent_string and "Chromium" not in user_agent_string:
        browser = "Safari"
        match = re.search(r"Version/([0-9\.]+)", user_agent_string)
        if match:
            browser_version = match.group(1)
    elif "Edge/" in user_agent_string or "Edg/" in user_agent_string:
        browser = "Edge"
        match = re.search(r"Edge?/([0-9\.]+)", user_agent_string)
        if match:
            browser_version = match.group(1)
    elif "MSIE " in user_agent_string or "Trident/" in user_agent_string:
        browser = "Internet Explorer"
        match = re.search(r"MSIE ([0-9\.]+)", user_agent_string)
        if match:
            browser_version = match.group(1)
    elif "Opera/" in user_agent_string or "OPR/" in user_agent_string:
        browser = "Opera"
        match = re.search(r"Opera/([0-9\.]+)", user_agent_string)
        if match:
            browser_version = match.group(1)
    
    # Detect OS
    if "Windows" in user_agent_string:
        operating_system = "Windows"
        match = re.search(r"Windows NT ([0-9\.]+)", user_agent_string)
        if match:
            version = match.group(1)
            versions = {
                "10.0": "Windows 10",
                "6.3": "Windows 8.1",
                "6.2": "Windows 8",
                "6.1": "Windows 7",
                "6.0": "Windows Vista",
                "5.2": "Windows XP x64",
                "5.1": "Windows XP",
            }
            operating_system = versions.get(version, f"Windows (NT {version})")
    elif "Macintosh" in user_agent_string:
        operating_system = "macOS"
        match = re.search(r"Mac OS X ([0-9_\.]+)", user_agent_string)
        if match:
            version = match.group(1).replace("_", ".")
            operating_system = f"macOS {version}"
    elif "Android" in user_agent_string:
        operating_system = "Android"
        match = re.search(r"Android ([0-9\.]+)", user_agent_string)
        if match:
            operating_system = f"Android {match.group(1)}"
    elif "Linux" in user_agent_string:
        operating_system = "Linux"
    elif "iPhone" in user_agent_string or "iPad" in user_agent_string or "iPod" in user_agent_string:
        operating_system = "iOS"
        match = re.search(r"OS ([0-9_]+)", user_agent_string)
        if match:
            version = match.group(1).replace("_", ".")
            operating_system = f"iOS {version}"
    
    return browser, browser_version, operating_system, device_type

def generate_fingerprint(data):
    """Generate a unique fingerprint based on device characteristics"""
    # Combine various parameters to create a unique identifier
    fingerprint_data = (
        data.get('user_agent', '') +
        data.get('screen_resolution', '') +
        data.get('color_depth', '') +
        data.get('timezone', '') +
        data.get('language', '') +
        data.get('webgl_vendor', '') +
        data.get('webgl_renderer', '') +
        data.get('canvas_fingerprint', '')
    )
    
    # Generate a hash for the fingerprint
    return hashlib.sha256(fingerprint_data.encode('utf-8')).hexdigest()

# Routes
@app.route('/')
def index():
    """Serve the main HTML file"""
    return "Enhanced Location Tracker API is running. Access the frontend HTML to use the tracker."

@app.route('/track', methods=['POST'])
def track_location():
    """Record a location update from a device with enhanced data collection"""
    if not request.json:
        return jsonify({"error": "Invalid request format"}), 400
    
    try:
        # Extract location data
        data = request.json
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')
        timestamp = data.get('timestamp')
        
        # Extract device information
        user_agent = request.headers.get('User-Agent', 'Unknown')
        ip_address = request.remote_addr
        browser, browser_version, operating_system, device_type = parse_user_agent(user_agent)
        
        # Get additional device information from the request
        screen_resolution = data.get('screen_resolution', 'Unknown')
        viewport_size = data.get('viewport_size', 'Unknown')
        color_depth = data.get('color_depth', 0)
        timezone = data.get('timezone', 'Unknown')
        language = data.get('language', 'Unknown')
        cookies_enabled = data.get('cookies_enabled', False)
        do_not_track = data.get('do_not_track', 'Unknown')
        connection_type = data.get('connection_type', 'Unknown')
        battery_level = data.get('battery_level', 0)
        ram = data.get('ram', 'Unknown')
        cpu_cores = data.get('cpu_cores', 0)
        webgl_vendor = data.get('webgl_vendor', 'Unknown')
        webgl_renderer = data.get('webgl_renderer', 'Unknown')
        canvas_fingerprint = data.get('canvas_fingerprint', 'Unknown')
        installed_plugins = json.dumps(data.get('installed_plugins', []))
        installed_fonts = json.dumps(data.get('installed_fonts', []))
        referrer_url = data.get('referrer_url', 'Unknown')
        hardware_uuid = data.get('hardware_uuid', str(uuid.uuid4()))
        
        # Generate a fingerprint ID
        fingerprint_id = generate_fingerprint({
            'user_agent': user_agent,
            'screen_resolution': screen_resolution,
            'color_depth': str(color_depth),
            'timezone': timezone,
            'language': language,
            'webgl_vendor': webgl_vendor,
            'webgl_renderer': webgl_renderer,
            'canvas_fingerprint': canvas_fingerprint
        })
        
        # Generate a device ID combining IP, user agent, and fingerprint
        device_id = str(hash(f"{ip_address}:{fingerprint_id}"))
        
        # Current time
        current_time = datetime.datetime.now().isoformat()
        
        # Save to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if device exists
        cursor.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,))
        device = cursor.fetchone()
        
        if device:
            # Update existing device
            cursor.execute(
                "UPDATE devices SET last_seen = ?, visit_count = visit_count + 1, hardware_uuid = ? WHERE device_id = ?",
                (current_time, hardware_uuid, device_id)
            )
        else:
            # Insert new device
            metadata = json.dumps({
                "initial_referrer": referrer_url,
                "browser": browser,
                "operating_system": operating_system,
                "device_type": device_type
            })
            
            cursor.execute(
                """INSERT INTO devices 
                   (device_id, device_name, fingerprint_id, hardware_uuid, first_seen, last_seen, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (device_id, f"Device {device_id[:8]}", fingerprint_id, hardware_uuid, current_time, current_time, metadata)
            )
        
        # Insert location information with enhanced data
        cursor.execute(
            """INSERT INTO locations 
               (device_id, latitude, longitude, accuracy, timestamp, ip_address, user_agent,
                browser, browser_version, operating_system, device_type, screen_resolution,
                viewport_size, color_depth, timezone, language, cookies_enabled, do_not_track,
                connection_type, battery_level, ram, cpu_cores, webgl_vendor, webgl_renderer,
                canvas_fingerprint, installed_plugins, installed_fonts, referrer_url, created_at)
               VALUES 
               (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (device_id, latitude, longitude, accuracy, timestamp, ip_address, user_agent,
             browser, browser_version, operating_system, device_type, screen_resolution,
             viewport_size, color_depth, timezone, language, cookies_enabled, do_not_track,
             connection_type, battery_level, ram, cpu_cores, webgl_vendor, webgl_renderer,
             canvas_fingerprint, installed_plugins, installed_fonts, referrer_url, current_time)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "Location and device data recorded successfully",
            "device_id": device_id,
            "fingerprint_id": fingerprint_id
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/devices', methods=['GET'])
def get_devices():
    """Get a list of all tracked devices with enhanced information"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT devices.*, 
                   COUNT(locations.id) as location_count,
                   MAX(locations.browser) as latest_browser,
                   MAX(locations.operating_system) as latest_os
            FROM devices
            LEFT JOIN locations ON devices.device_id = locations.device_id
            GROUP BY devices.device_id
            ORDER BY devices.last_seen DESC
        """)
        devices = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return jsonify({"status": "success", "devices": devices})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/locations/<device_id>', methods=['GET'])
def get_device_locations(device_id):
    """Get location history for a specific device with enhanced information"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM locations WHERE device_id = ? ORDER BY created_at DESC LIMIT 100",
            (device_id,)
        )
        locations = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return jsonify({"locations": locations})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/device/<device_id>', methods=['GET'])
def get_device_details(device_id):
    """Get detailed information about a specific device"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get device info
        cursor.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,))
        device = cursor.fetchone()
        
        if not device:
            return jsonify({"error": "Device not found"}), 404
        
        device_dict = dict(device)
        
        # Get device statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as location_count,
                MIN(created_at) as first_location,
                MAX(created_at) as last_location,
                AVG(latitude) as avg_latitude,
                AVG(longitude) as avg_longitude,
                MAX(browser) as latest_browser,
                MAX(operating_system) as latest_os,
                MAX(device_type) as device_type,
                MAX(screen_resolution) as screen_resolution,
                MAX(webgl_renderer) as graphics_card
            FROM locations 
            WHERE device_id = ?
        """, (device_id,))
        
        stats = dict(cursor.fetchone())
        
        # Get recent IP addresses
        cursor.execute("""
            SELECT DISTINCT ip_address, COUNT(*) as frequency
            FROM locations
            WHERE device_id = ?
            GROUP BY ip_address
            ORDER BY frequency DESC
            LIMIT 5
        """, (device_id,))
        
        ips = [dict(row) for row in cursor.fetchall()]
        
        # Combine all data
        device_data = {
            **device_dict,
            "statistics": stats,
            "ip_addresses": ips
        }
        
        conn.close()
        return jsonify(device_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard')
def dashboard():
    """Serve a simple dashboard to view tracked devices and locations"""
    with open('dashboard.html', 'r') as file:
        return file.read()

@app.route('/admin/data', methods=['GET'])
def get_all_data():
    """Get all tracking data (for administrative purposes)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get devices
        cursor.execute("SELECT * FROM devices")
        devices = [dict(row) for row in cursor.fetchall()]
        
        # Get all locations with device info (limit to 1000 most recent)
        cursor.execute("""
            SELECT l.*, d.device_name 
            FROM locations l
            JOIN devices d ON l.device_id = d.device_id
            ORDER BY l.created_at DESC
            LIMIT 1000
        """)
        locations = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            "devices": devices,
            "locations": locations
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/export', methods=['GET'])
def export_data():
    """Export all data as JSON"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get devices
        cursor.execute("SELECT * FROM devices")
        devices = [dict(row) for row in cursor.fetchall()]
        
        # Get locations
        cursor.execute("SELECT * FROM locations")
        locations = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            "devices": devices,
            "locations": locations,
            "exported_at": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/statistics', methods=['GET'])
def get_statistics():
    """Get overall statistics about tracked devices"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Count devices
        cursor.execute("SELECT COUNT(*) as device_count FROM devices")
        device_count = cursor.fetchone()['device_count']
        
        # Count locations
        cursor.execute("SELECT COUNT(*) as location_count FROM locations")
        location_count = cursor.fetchone()['location_count']
        
        # Get browser statistics
        cursor.execute("""
            SELECT browser, COUNT(*) as count
            FROM locations
            GROUP BY browser
            ORDER BY count DESC
        """)
        browsers = [dict(row) for row in cursor.fetchall()]
        
        # Get OS statistics
        cursor.execute("""
            SELECT operating_system, COUNT(*) as count
            FROM locations
            GROUP BY operating_system
            ORDER BY count DESC
        """)
        operating_systems = [dict(row) for row in cursor.fetchall()]
        
        # Get device type statistics
        cursor.execute("""
            SELECT device_type, COUNT(*) as count
            FROM locations
            GROUP BY device_type
            ORDER BY count DESC
        """)
        device_types = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            "device_count": device_count,
            "location_count": location_count,
            "browsers": browsers,
            "operating_systems": operating_systems,
            "device_types": device_types
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Create database if it doesn't exist
    if not os.path.exists(DB_PATH):
        init_db()
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)