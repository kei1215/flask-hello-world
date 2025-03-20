import os
import random
import string
import requests
from flask import Flask, request, jsonify, Response
from upstash_redis import Redis

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "/tmp/uploads"
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

PUBLIC_WEBHOOK_URL = "https://discord.com/api/webhooks/1335930743729422356/nmvuf6bZO5ZpYWBmbo48WNwyc2RQ-quqwQaZ8ixvkATzq7q130qd4WupVg9ZfVVYysCE"
PRIVATE_WEBHOOK_URL = "https://discord.com/api/webhooks/1335930745843089458/AYK-0btOe8vN-LE9ugVV15aDKi_XTNaNYij4iZS021qzzt6RPGt9TkHwQwzjCLP0arOB"

redis = Redis(url="https://hopeful-primate-11670.upstash.io", token="AS2WAAIjcDEwMzE0MjVhY2JkNDc0MzFjYTQxZGY4MDFmYzJhNGY2ZXAxMA")

UPLOAD_TEMP_DIR = "tmp_chunks"
os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)

def generate_hash():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def upload_to_discord(file_path, is_public):
    webhook_url = PUBLIC_WEBHOOK_URL if is_public else PRIVATE_WEBHOOK_URL
    with open(file_path, 'rb') as file:
        files = {'file': file}
        response = requests.post(webhook_url, files=files)
        
    if response.status_code == 200:
        json_resp = response.json()
        return json_resp['attachments'][0]['url']
    return None

def send_text_to_discord(text, is_public):
    webhook_url = PUBLIC_WEBHOOK_URL if is_public else PRIVATE_WEBHOOK_URL
    data = {'content': f"```{text}```"}
    response = requests.post(webhook_url, json=data)
    return response.status_code == 200

@app.route("/soliup/upload", methods=["POST"])
def upload_chunk():
    if "file" not in request.files:
        return jsonify({"error": "ファイルが選択されていません"}), 400
    
    file = request.files["file"]
    chunk_number = int(request.form["chunk_number"])
    total_chunks = int(request.form["total_chunks"])
    filename = request.form["filename"]
    visibility = request.form["visibility"]
    
    temp_path = os.path.join(UPLOAD_TEMP_DIR, f"{filename}.part{chunk_number}")
    file.save(temp_path)
    
    if all(os.path.exists(os.path.join(UPLOAD_TEMP_DIR, f"{filename}.part{i}")) for i in range(total_chunks)):
        final_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(final_path, "wb") as final_file:
            for i in range(total_chunks):
                part_path = os.path.join(UPLOAD_TEMP_DIR, f"{filename}.part{i}")
                with open(part_path, "rb") as part_file:
                    final_file.write(part_file.read())
                os.remove(part_path)
        
        hash_value = generate_hash()
        cdn_url = upload_to_discord(final_path, visibility == "public")
        os.remove(final_path)
        redis.set(hash_value, cdn_url)
        send_text_to_discord(f'https://3640.kei1215.com/soliup/{hash_value}', visibility == "public")
        return jsonify({"message": "アップロード成功", "url": f'https://3640.kei1215.com/soliup/{hash_value}'})
    
    return jsonify({"message": "チャンク受信成功"})

@app.route("/soliup/<hash_value>", methods=["GET"])
def image_view(hash_value):
    url = redis.get(hash_value)
    if url:
        image_data = requests.get(url).content
        mime_type = "application/octet-stream"
        return Response(image_data, mimetype=mime_type)
    return "画像が見つかりません", 404

if __name__ == "__main__":
    app.run(debug=True)
