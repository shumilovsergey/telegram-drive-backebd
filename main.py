from flask import Flask, request, jsonify
import redis
import json
import os

app = Flask(__name__)

redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, decode_responses=True)
try:
    redis_client.ping()
    print("Connected to Redis!")
except redis.exceptions.ConnectionError as e:
    print("Redis connection failed:", e)
    exit(1)


@app.route('/get_data', methods=['POST'])
def get_data():
    req = request.get_json()

    if not req or 'user_id' not in req:
        return jsonify({"error": "Missing user_id"}), 400

    user_id = req['user_id']
    user_key = f"user:{user_id}"
    user_data = redis_client.get(user_key)

    if user_data:
        return jsonify({"user_id": user_id, "user_data": json.loads(user_data)})

    # Create default user if not exists
    default_data = {"level": 1, "progress": 0}
    redis_client.set(user_key, json.dumps(default_data))

    return jsonify({"user_id": user_id, "user_data": default_data})


@app.route('/up_data', methods=['POST'])
def up_data():
    req = request.get_json()

    if not req or 'user_id' not in req or 'user_data' not in req:
        return jsonify({"error": "Missing user_id or user_data"}), 400

    user_id = req['user_id']
    user_data = req['user_data']
    user_key = f"user:{user_id}"

    redis_client.set(user_key, json.dumps(user_data))

    return jsonify({"message": "User data updated", "user_id": user_id})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
