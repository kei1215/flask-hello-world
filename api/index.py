import os
import random
import string
import requests
import json
import mimetypes
from upstash_redis import Redis
from flask import Flask, request, render_template, jsonify, Response, redirect

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

# 📌 Discord Webhook URLs (公開枠 & 限定公開枠)
PUBLIC_WEBHOOK_URL = "https://discord.com/api/webhooks/1360812996577984593/cFJE87V0bDmMKqPQL4k3zTAg_abP3unfiWc5Z2WOU7QOkpBIPTU5fdZR_sX-lRmSxBmk"
PRIVATE_WEBHOOK_URL = "https://discord.com/api/webhooks/1360813192259047606/1C9r5fkvREgXSXw8OVXPgYWEc-TwdH6uRD-t9r7lnWDsRxKQoqYdAY4lYuignpXFdx6Q"
JOINT_WEBHOOOK_URL = "https://discord.com/api/webhooks/1367153610831695934/73cNYAmB9-5j7t-EjgYjBrL3fFu-44FKZO_5ThEpbtG8p6zewq0LPI2we3_EIf8e4J96"
redis = Redis(url="https://hopeful-primate-11670.upstash.io", token="AS2WAAIjcDEwMzE0MjVhY2JkNDc0MzFjYTQxZGY4MDFmYzJhNGY2ZXAxMA")

EXTENSION_TO_MIMETYPE = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
    "svg": "image/svg+xml",
    "mp4": "video/mp4",
    "webm": "video/webm",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
}

# 📌 一時ファイル保存フォルダ
UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def generate_hash():
    """8桁の一意なランダムハッシュを生成"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def upload_to_discord(message, hash, file_path, is_public):
    """画像をDiscordにアップロードし、CDNのURLを取得"""
    
    WEBHOOK_URL = PUBLIC_WEBHOOK_URL if is_public == "1" else PRIVATE_WEBHOOK_URL if is_public == "2" else JOINT_WEBHOOOK_URL
    data = {
        'content': f"{message}\n共有URL```https://3640.kei1215.com/soliup/{hash}```削除URL```https://3640.kei1215.com/del/{hash}```"  # 送信したいテキスト
    }
    files = {'file': open(file_path, 'rb')}
    response = requests.post(WEBHOOK_URL, data=data, files=files)
    files['file'].close()
    
    if response.status_code == 200:
        json_resp = response.json()
        parts = urlparse(WEBHOOK_URL).path.split("/")
        webhook_id = parts[-2]
        webhook_token = parts[-1]
        message_id = json_resp.get("id")
        attachment = json_resp.get("attachments", [{}])[0]
        image_url = attachment.get("url", "")
        delete_url = f"https://discord.com/api/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}"
        return {
            "image_url": image_url,
            "delete_url": delete_url
        }
    return None

import requests
from urllib.parse import urlparse

def allowed_file(filename):
    # 拡張子を小文字にして取得
    ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.mp4', '.mov', '.avi', '.mkv', '.mp3', '.wav', '.flac'}
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

@app.route('/invite')
def redirect_func():
    return redirect('https://discord.gg/7T8rq3ewg8')

@app.route("/soliup/", methods=["GET"])
def index():
    """アップロードページを表示"""
    return render_template("upload.html")

@app.route("/soliup/upload", methods=["POST"])
def upload():
    """画像をアップロードし、Discord → Pastebin に保存"""
    if "file" not in request.files:
        return "ファイルが選択されていません"
    
    file = request.files["file"]
    if file.filename == "":
        return "ファイルがありません"
    
    # ✅ 公開設定を取得
    is_public = request.form.get("visibility")
    message = request.form.get("message")
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only images are allowed.'}), 400
    # ✅ ファイルを保存
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    hash = generate_hash()
    
    cdn_url = upload_to_discord(message, hash, file_path, is_public)
    os.remove(file_path)  # アップロード後、ローカルから削除
    redis.set(hash, json.dumps(cdn_url))
    if cdn_url:
        return f"アップロード成功！画像URL: <a href='https://3640.kei1215.com/soliup/{hash}'>https://3640.kei1215.com/soliup/{hash}</a>"
    return "アップロードに失敗しました"

@app.route("/soliup/<hash_value>", methods=["GET"])
def image_view(hash_value):
    """ハッシュ値に対応する画像を取得し表示"""
    url = json.loads(redis.get(hash_value))
    print(url)
    if url:
        image_data = requests.get(url['image_url']).content  # URLから画像データを取得
        
        # ファイルの拡張子からMIMEタイプを取得
        mime_type = EXTENSION_TO_MIMETYPE.get(url.split('?')[0].split('.')[-1].lower(), "application/octet-stream")
        if not mime_type:
            mime_type = "application/octet-stream"  # 不明な場合は汎用バイナリデータ
            
        return Response(image_data, mimetype=mime_type)
    
    return "画像が見つかりません", 404

if __name__ == "__main__":
    app.run(debug=True)
