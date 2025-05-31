from flask import Blueprint, request, jsonify
from app import redis_client, valid_token
import json

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

    default_data = {"level": 1, "progress": 0}
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
