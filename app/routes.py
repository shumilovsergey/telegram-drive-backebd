import json, requests
from flask import Blueprint, request, jsonify
from app import redis_client, valid_token, telegram_token

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
    print("🔔 Telegram update:", update)

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
            print("this is file")

            # 1) extract file_id (photos come as a list of sizes)
            if field == "photo":
                file_id = message["photo"][-1]["file_id"]
            else:
                file_id = message[field]["file_id"]

            # 2) check/create user in Redis
            user_key = f"user:{chat_id}"
            raw = redis_client.get(user_key)
            if raw:
                data = json.loads(raw)
            else:
                data = {}    # start fresh
            # 3) add this file_id to user_data.files list
            files = data.get("files", [])
            files.append(file_id)
            data["files"] = files
            redis_client.set(user_key, json.dumps(data))

        # 4) delete the user’s message in Telegram
        del_url = f"https://api.telegram.org/bot{telegram_token}/deleteMessage"
        requests.post(del_url, json={
            "chat_id": chat_id,
            "message_id": msg_id
        })
        break

    return jsonify({"status": "ok"}), 200