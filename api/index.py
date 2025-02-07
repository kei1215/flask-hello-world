import os
import random
import string
import requests
from flask import Flask, request, render_template, jsonify, Response
from upstash_redis import Redis

app = Flask(__name__)

# 📌 Discord Webhook URLs (公開枠 & 限定公開枠)
PUBLIC_WEBHOOK_URL = "https://discord.com/api/webhooks/1335930743729422356/nmvuf6bZO5ZpYWBmbo48WNwyc2RQ-quqwQaZ8ixvkATzq7q130qd4WupVg9ZfVVYysCE"
PRIVATE_WEBHOOK_URL = "https://discord.com/api/webhooks/1335930745843089458/AYK-0btOe8vN-LE9ugVV15aDKi_XTNaNYij4iZS021qzzt6RPGt9TkHwQwzjCLP0arOB"

redis = Redis(url="https://hopeful-primate-11670.upstash.io", token="AS2WAAIjcDEwMzE0MjVhY2JkNDc0MzFjYTQxZGY4MDFmYzJhNGY2ZXAxMA")




# 📌 一時ファイル保存フォルダ
UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.mp4', '.mov', '.avi', '.mkv', '.mp3', '.wav', '.flac'}

def generate_hash():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def upload_to_discord(file_path, is_public):
    webhook_url = PUBLIC_WEBHOOK_URL if is_public else PRIVATE_WEBHOOK_URL
    files = {'file': open(file_path, 'rb')}
    response = requests.post(webhook_url, files=files)
    files['file'].close()
    
    if response.status_code == 200:
        json_resp = response.json()
        return json_resp['attachments'][0]['url']
    return None

def save_to_edgedb(hash_value, cdn_url, is_public):
    redis.set(hash_value, cdn_url)

def get_file_from_edgedb(hash_value):
    return redis.get(hash_value)

@app.route("/", methods=["GET"])
def index():
    return render_template("upload.html")

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return "ファイルが選択されていません"
    
    file = request.files["file"]
    if file.filename == "" or os.path.splitext(file.filename)[1].lower() not in ALLOWED_EXTENSIONS:
        return jsonify({'error': 'Invalid file type'}), 400
    
    is_public = request.form.get("visibility") == "public"
    hash_value = generate_hash()
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    
    cdn_url = upload_to_discord(file_path, is_public)
    os.remove(file_path)
    
    if cdn_url:
        save_to_edgedb(hash_value, cdn_url, is_public)
        return f"アップロード成功！ファイルURL: <a href='/view/{hash_value}'>こちら</a>"
    
    return "アップロードに失敗しました"

@app.route("/view/<hash_value>", methods=["GET"])
def view_file(hash_value):
    file_data = get_file_from_edgedb(hash_value)
    if file_data:
        return render_template("view.html", file_url=file_data.url, is_public=file_data.is_public)
    return "ファイルが見つかりません", 404

if __name__ == "__main__":
    app.run(debug=True)
