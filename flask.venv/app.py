from flask import Flask, jsonify, request
import csv
import os

app = Flask(__name__)
FILE_NAME = 'data.csv'

def read_logs():
    logs = []
    if not os.path.exists(FILE_NAME):
        return logs
    with open(FILE_NAME, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                logs.append({
                    "user_id": row[0].strip(),
                    "log_id": row[1].strip(),
                    "first_name": row[2].strip(),
                    "last_name": row[3].strip(),
                    "email": row[4].strip(),
                    "url": row[5].strip(),
                    "status_code": row[6].strip()
                })
    return logs

def write_logs(logs):
    with open(FILE_NAME, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for log in logs:
            writer.writerow([
                log['user_id'], log['log_id'], log['first_name'],
                log['last_name'], log['email'], log['url'], log['status_code']
            ])

@app.route('/logs', methods=['GET'])
def get_logs():
    return jsonify(read_logs())

@app.route('/logs/<id>', methods=['GET'])
def get_log_by_id(id):
    logs = read_logs()
    log = next((l for l in logs if l['log_id'] == id), None)
    return jsonify(log) if log else (jsonify({"error": "Not found"}), 404)

@app.route('/logs', methods=['POST'])
def add_log():
    data = request.json
    logs = read_logs()
    
    new_id = 1
    if logs:
        new_id = max(int(l['log_id']) for l in logs) + 1
    
    new_log = {
        "user_id": str(data['user_id']),
        "log_id": str(new_id),
        "first_name": data['first_name'],
        "last_name": data['last_name'],
        "email": data['email'],
        "url": data['url'],
        "status_code": str(data['status_code'])
    }
    
    logs.append(new_log)
    write_logs(logs)
    return jsonify(new_log), 201

@app.route('/logs/<log_id>', methods=['DELETE'])
def delete_log(log_id):
    logs = read_logs()
    new_logs = [l for l in logs if l['log_id'] != log_id]
    if len(logs) == len(new_logs):
        return jsonify({"error": "Not found"}), 404
    write_logs(new_logs)
    return jsonify({"message": "Deleted"}), 200

@app.route('/users/<user_id>/logs', methods=['GET'])
def get_user_logs(user_id):
    logs = read_logs()
    user_logs = [l for l in logs if l['user_id'] == user_id]
    return jsonify(user_logs)

@app.route('/users/', methods=['GET'])
def get_users():
    logs = read_logs()
    users = {}
    for l in logs:
        uid = l['user_id']
        if uid not in users:
            users[uid] = {
                "user_id": uid,
                "first_name": l['first_name'],
                "last_name": l['last_name'],
                "email": l['email']
            }
    return jsonify(list(users.values()))

if __name__ == '__main__':
    app.run(debug=True)