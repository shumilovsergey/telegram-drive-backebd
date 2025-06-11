import json, requests
from flask import Blueprint, request, jsonify
from app import redis_client, valid_token, telegram_token
from datetime import datetime

API_URL = "http://localhost:8080"

bp = Blueprint('routes', __name__)

def check_token(req_json):
    token = req_json.get("token")
    return token == valid_token


@bp.route('/get_data', methods=['POST'])
def get_data():
    req = request.get_json()

    if not check_token(req):
        return jsonify({"error": "Invalid or missing token"}), 403

    if 'user_id' not in req:
        return jsonify({"error": "Missing user_id"}), 400

    user_id = req['user_id']
    user_key = f"user:{user_id}"
    user_data = redis_client.get(user_key)

    if user_data:
        return jsonify({"user_id": user_id, "user_data": json.loads(user_data)})

    default_data = []
    redis_client.set(user_key, json.dumps(default_data))
    print(f"user_id {user_id}")
    print(f"user_data {default_data}")
    return jsonify({"user_id": user_id, "user_data": default_data})


@bp.route('/up_data', methods=['POST'])
def up_data():
    req = request.get_json()

    if not check_token(req):
        return jsonify({"error": "Invalid or missing token"}), 403

    if 'user_id' not in req or 'user_data' not in req:
        return jsonify({"error": "Missing user_id or user_data"}), 400

    user_id = req['user_id']
    user_data = req['user_data']
    user_key = f"user:{user_id}"

    redis_client.set(user_key, json.dumps(user_data))

    return jsonify({"message": "User data updated", "user_id": user_id})

@bp.route('/telegram', methods=['POST'])
def telegram_webhook():
    update = request.get_json()

    message = update.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    msg_id  = message.get("message_id")
    text = message.get("text")

    if text == "/start":
        # … existing /start logic …
        return jsonify({"status": "ok"}), 200

    # detect any file-type field
    file_fields = ["photo", "document", "audio", "video", "voice"]
    for field in file_fields:
        if field in message:
            if field == "photo":
                file_id = message["photo"][-1]["file_id"]
                # photos don’t have names, so we’ll use file_id.jpg
                now = datetime.now()
                time_stemp = now.strftime("%H:%M-%d.%m.%y")
                file_name = f"{time_stemp}.jpg"

            else:
                doc = message[field]
                file_id = doc["file_id"]
                # for documents, Telegram provides a file_name
                file_name = doc.get("file_name", file_id)
                
            resp = requests.post(f"{API_URL}/get_data", json={
                "user_id": chat_id,
                "token": valid_token
            })

            data = resp.json()
            user_data = data.get("user_data", [])

            new_file = {
                "file_id": file_id,
                "file_type": "",
                "file_path": f"/tgDrive/{file_name}"
            }

            user_data.append(new_file)

            response = requests.post(f"{API_URL}/up_data", json={
                "user_id": chat_id,
                "token": valid_token,
                "user_data": user_data
            })

        # 4) delete the user’s message in Telegram
        del_url = f"https://api.telegram.org/bot{telegram_token}/deleteMessage"
        requests.post(del_url, json={
            "chat_id": chat_id,
            "message_id": msg_id
        })
        break

    return jsonify({"status": "ok"}), 200


@bp.route('/download', methods=['POST'])
def download():
    req = request.get_json()

    if not check_token(req):
        return jsonify({"error": "Invalid or missing token"}), 403

    user_id = req.get("user_id")
    file_id = req.get("file_id")
    if not user_id or not file_id:
        return jsonify({"error": "Missing user_id or file_id"}), 400
    
    send_url = f"https://api.telegram.org/bot{telegram_token}/sendDocument"
    payload = {
        "chat_id": user_id,
        "document": file_id
    }
    tg_response = requests.post(send_url, json=payload)

    return jsonify({"status": "ok"}), 200