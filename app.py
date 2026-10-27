from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)

DB_FILE = "minizo.db"
SECRET_BOT_KEY = "BOT_SECRET_123"
SECRET_APP_KEY = "APP_SECRET_456"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_code TEXT UNIQUE,
        device_id TEXT,
        created_at TIMESTAMP,
        expires_at TIMESTAMP,
        status TEXT DEFAULT 'UNUSED'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS devices (
        device_id TEXT PRIMARY KEY,
        device_name TEXT,
        ip_address TEXT,
        carrier TEXT,
        android_version TEXT,
        last_login TIMESTAMP,
        key_code TEXT,
        last_seen TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS blacklist (
        device_id TEXT PRIMARY KEY,
        reason TEXT,
        banned_at TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS login_attempts (
        device_id TEXT PRIMARY KEY,
        fail_count INTEGER DEFAULT 0,
        locked_until TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS server_config (
        id INTEGER PRIMARY KEY,
        status TEXT DEFAULT 'ACTIVE',
        update_message TEXT
    )''')
    c.execute("INSERT OR IGNORE INTO server_config (id, status, update_message) VALUES (1, 'ACTIVE', '')")
    conn.commit()
    conn.close()

init_db()

def check_bot_auth(): return request.headers.get("X-Bot-Key") == SECRET_BOT_KEY
def check_app_auth(): return request.headers.get("X-App-Key") == SECRET_APP_KEY

@app.route('/api/bot', methods=['POST'])
def bot_command():
    if not check_bot_auth(): return jsonify({"status": "ERROR", "message": "Unauthorized"}), 401
    data = request.json
    action = data.get('action')
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    try:
        if action == 'create_key':
            key = data.get('key_code')
            hours = int(data.get('hours', 0))
            expires = None if hours == 0 else (datetime.now() + timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            try:
                c.execute("INSERT INTO keys (key_code, created_at, expires_at) VALUES (?, ?, ?)", (key, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), expires))
                conn.commit()
                return jsonify({"status": "OK", "message": f"Đã tạo key {key}"})
            except:
                return jsonify({"status": "ERROR", "message": "Key đã tồn tại"})

        elif action == 'delete_key':
            key = data.get('key_code')
            c.execute("DELETE FROM keys WHERE key_code = ?", (key,))
            conn.commit()
            return jsonify({"status": "OK", "message": f"Đã xóa key {key}"})

        elif action == 'get_key_info':
            key = data.get('key_code')
            c.execute("SELECT * FROM keys WHERE key_code = ?", (key,))
            row = c.fetchone()
            if row: return jsonify({"status": "OK", "data": row})
            return jsonify({"status": "ERROR", "message": "Key không tồn tại"})

        elif action == 'all_devices':
            c.execute("SELECT * FROM devices ORDER BY last_login DESC")
            rows = c.fetchall()
            return jsonify({"status": "OK", "data": rows})

        elif action == 'device_info':
            idx = int(data.get('index', 1)) - 1
            c.execute("SELECT * FROM devices ORDER BY last_login DESC LIMIT 1 OFFSET ?", (idx,))
            row = c.fetchone()
            if row: return jsonify({"status": "OK", "data": row})
            return jsonify({"status": "ERROR", "message": "Không tìm thấy máy"})

        elif action == 'kick_device':
            dev_id = data.get('device_id')
            c.execute("UPDATE devices SET key_code = NULL WHERE device_id = ?", (dev_id,))
            c.execute("UPDATE keys SET device_id = NULL, status = 'UNUSED' WHERE device_id = ?", (dev_id,))
            conn.commit()
            return jsonify({"status": "OK", "message": f"Đã đá máy {dev_id} ra khỏi App"})

        elif action == 'reset_device':
            key = data.get('key_code')
            c.execute("UPDATE keys SET device_id = NULL, status = 'UNUSED' WHERE key_code = ?", (key,))
            conn.commit()
            return jsonify({"status": "OK", "message": f"Đã reset máy cho key {key}"})

        elif action == 'blacklist':
            dev_id = data.get('device_id')
            c.execute("INSERT OR REPLACE INTO blacklist (device_id, reason, banned_at) VALUES (?, ?, ?)", (dev_id, "Vi phạm", datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            return jsonify({"status": "OK", "message": f"Đã ban {dev_id}"})

        elif action == 'unblacklist':
            dev_id = data.get('device_id')
            c.execute("DELETE FROM blacklist WHERE device_id = ?", (dev_id,))
            conn.commit()
            return jsonify({"status": "OK", "message": f"Đã gỡ ban {dev_id}"})

        elif action == 'stats':
            c.execute("SELECT COUNT(*) FROM devices")
            total_dev = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM keys")
            total_key = c.fetchone()[0]
            return jsonify({"status": "OK", "message": f"Tổng máy: {total_dev} | Tổng Key: {total_key}"})

        elif action == 'online_devices':
            two_min_ago = (datetime.now() - timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S')
            c.execute("SELECT device_id, device_name, ip_address, last_seen FROM devices WHERE last_seen > ? ORDER BY last_seen DESC", (two_min_ago,))
            rows = c.fetchall()
            return jsonify({"status": "OK", "data": rows})

        elif action == 'lock_update':
            c.execute("UPDATE server_config SET status = 'LOCKED', update_message = ? WHERE id = 1", (data.get('message', 'Ứng dụng đang cập nhật'),))
            conn.commit()
            return jsonify({"status": "OK", "message": "Đã khóa toàn bộ App"})

        elif action == 'unlock_update':
            c.execute("UPDATE server_config SET status = 'ACTIVE' WHERE id = 1")
            conn.commit()
            return jsonify({"status": "OK", "message": "Đã mở khóa App"})

        elif action == 'delete_all':
            c.execute("DELETE FROM keys")
            c.execute("DELETE FROM devices")
            c.execute("DELETE FROM blacklist")
            c.execute("DELETE FROM login_attempts")
            conn.commit()
            return jsonify({"status": "OK", "message": "Đã xóa toàn bộ dữ liệu"})

    finally:
        conn.close()
    
    return jsonify({"status": "ERROR", "message": "Lệnh không hợp lệ"})

@app.route('/api/check_key', methods=['POST'])
def check_key():
    if not check_app_auth(): return jsonify({"status": "ERROR", "message": "Unauthorized"}), 401
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        c.execute("SELECT status, update_message FROM server_config WHERE id = 1")
        config = c.fetchone()
        if config and config[0] == 'LOCKED':
            return jsonify({"status": "LOCKED", "message": config[1]})

        data = request.json
        key_code = data.get('key_code')
        device_id = data.get('device_id')
        device_name = data.get('device_name', 'Unknown')
        ip = data.get('ip', '0.0.0.0')
        carrier = data.get('carrier', 'Unknown')
        android_ver = data.get('android_version', 'Unknown')

        if not key_code or not device_id:
            return jsonify({"status": "ERROR", "message": "Missing data"}), 400

        c.execute("SELECT * FROM blacklist WHERE device_id = ?", (device_id,))
        if c.fetchone():
            return jsonify({"status": "ERROR", "message": "Máy bạn đã bị blacklist. Liên hệ Admin!"})

        c.execute("SELECT locked_until FROM login_attempts WHERE device_id = ?", (device_id,))
        lock = c.fetchone()
        if lock and lock[0]:
            locked_until = datetime.strptime(lock[0], '%Y-%m-%d %H:%M:%S')
            if datetime.now() < locked_until:
                rem = int((locked_until - datetime.now()).total_seconds() / 60)
                return jsonify({"status": "ERROR", "message": f"Bạn đã nhập sai 3 lần. Bị khóa {rem} phút!"})
            else:
                c.execute("UPDATE login_attempts SET fail_count = 0, locked_until = NULL WHERE device_id = ?", (device_id,))
                conn.commit()

        c.execute("SELECT * FROM keys WHERE key_code = ?", (key_code,))
        row = c.fetchone()

        if not row:
            msg = "Key không tồn tại"
            success = False
        else:
            key_id, key_code_db, device_id_db, created_at, expires_at, status = row
            if expires_at and datetime.now() > datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S'):
                msg = "Key đã hết hạn"
                success = False
            elif status == 'BANNED':
                msg = "Key đã bị khóa"
                success = False
            elif device_id_db is None:
                c.execute("UPDATE keys SET device_id = ?, status = 'ACTIVE' WHERE key_code = ?", (device_id, key_code))
                success = True
                msg = "Kích hoạt thành công"
            elif device_id_db == device_id:
                success = True
                msg = "Đăng nhập thành công"
            else:
                msg = "Key đã dùng trên máy khác"
                success = False

        if success:
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute("INSERT OR REPLACE INTO devices (device_id, device_name, ip_address, carrier, android_version, last_login, key_code, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (device_id, device_name, ip, carrier, android_ver, now_str, key_code, now_str))
            c.execute("UPDATE login_attempts SET fail_count = 0, locked_until = NULL WHERE device_id = ?", (device_id,))
            conn.commit()
            return jsonify({"status": "OK", "message": msg})
        else:
            c.execute("SELECT fail_count FROM login_attempts WHERE device_id = ?", (device_id,))
            att = c.fetchone()
            if att:
                fail_count = att[0] + 1
                if fail_count >= 3:
                    locked_until = (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
                    c.execute("UPDATE login_attempts SET fail_count = ?, locked_until = ? WHERE device_id = ?", (fail_count, locked_until, device_id))
                    msg = "Sai 3 lần. Bị khóa 10 phút!"
                else:
                    c.execute("UPDATE login_attempts SET fail_count = ? WHERE device_id = ?", (fail_count, device_id))
                    msg = f"Sai key ({fail_count}/3)"
            else:
                c.execute("INSERT INTO login_attempts (device_id, fail_count) VALUES (?, 1)", (device_id,))
                msg = "Sai key (1/3)"
            conn.commit()
            return jsonify({"status": "ERROR", "message": msg})

    finally:
        conn.close()

@app.route('/api/check_status', methods=['POST'])
def check_status():
    if not check_app_auth(): return jsonify({"status": "ERROR", "message": "Unauthorized"}), 401
    
    data = request.json
    device_id = data.get('device_id')
    if not device_id:
        return jsonify({"status": "ERROR", "message": "Missing device_id"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("SELECT device_id FROM devices WHERE device_id = ?", (device_id,))
        if c.fetchone():
            c.execute("UPDATE devices SET last_seen = ? WHERE device_id = ?", (now_str, device_id))
        else:
            c.execute("INSERT INTO devices (device_id, last_seen) VALUES (?, ?)", (device_id, now_str))
        conn.commit()

        c.execute("SELECT * FROM blacklist WHERE device_id = ?", (device_id,))
        if c.fetchone():
            return jsonify({"status": "BANNED", "message": "Máy bạn đã bị blacklist. Liên hệ Admin!"})

        c.execute("SELECT status FROM server_config WHERE id = 1")
        config = c.fetchone()
        if config and config[0] == 'LOCKED':
            return jsonify({"status": "LOCKED", "message": "Ứng dụng đang cập nhật"})

        c.execute("SELECT key_code FROM devices WHERE device_id = ?", (device_id,))
        row = c.fetchone()
        if not row or row[0] is None:
            return jsonify({"status": "KICKED", "message": "Phiên đăng nhập đã hết hạn"})

        return jsonify({"status": "OK", "message": "Hợp lệ"})
    finally:
        conn.close()

@app.route('/ping', methods=['GET'])
def ping():
    return "ALIVE"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
