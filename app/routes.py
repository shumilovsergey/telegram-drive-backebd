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
    print("Telegram update:", update)

    message = update.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    msg_id  = message.get("message_id")
    user_key = f"user:{chat_id}"

    text = message.get("text")
    if text == "/start":
        # … existing /start logic …
        return jsonify({"status": "ok"}), 200

    # detect any file-type field
    file_fields = ["photo", "document", "audio", "video", "voice"]
    for field in file_fields:
        if field in message:
            print("this is file")

            # 1) extract file_id and file_name / file_type
            if field == "photo":
                file_id = message["photo"][-1]["file_id"]
                # photos don’t have names, so we’ll use file_id.jpg
                file_name = f"{file_id}.jpg"
                file_type = "picture"
            else:
                doc = message[field]
                file_id = doc["file_id"]
                # for documents, Telegram provides a file_name
                file_name = doc.get("file_name", file_id)
                # derive file_type from extension (or fallback to field name)
                if "." in file_name:
                    file_type = file_name.rsplit(".", 1)[1]
                else:
                    file_type = field

            # 2) build your entry object
            entry = {
                "file_id":   file_id,
                "file_type": file_type,
                "file_path": f"/downloads/{file_name}"
            }

            # 3) load existing data
            raw = redis_client.get(user_key)
            if raw:
                stored = json.loads(raw)
                if isinstance(stored, dict) and "user_data" in stored:
                    files_list = stored["user_data"]
                elif isinstance(stored, list):
                    # old format: just a list
                    files_list = stored
                else:
                    # other unexpected format
                    files_list = []
            else:
                files_list = []

            # 4) append new entry
            files_list.append(entry)

            # 5) save back as {"user_data": [...]}
            redis_client.set(user_key, json.dumps({ "user_data": files_list }))


        # 4) delete the user’s message in Telegram
        del_url = f"https://api.telegram.org/bot{telegram_token}/deleteMessage"
        requests.post(del_url, json={
            "chat_id": chat_id,
            "message_id": msg_id
        })
        break

    return jsonify({"status": "ok"}), 200