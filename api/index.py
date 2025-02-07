import os
import random
import string
import requests
import mimetypes
from upstash_redis import Redis
from flask import Flask, request, render_template, jsonify, Response

app = Flask(__name__)

# 📌 Discord Webhook URLs (公開枠 & 限定公開枠)
PUBLIC_WEBHOOK_URL = "https://discord.com/api/webhooks/1335930743729422356/nmvuf6bZO5ZpYWBmbo48WNwyc2RQ-quqwQaZ8ixvkATzq7q130qd4WupVg9ZfVVYysCE"
PRIVATE_WEBHOOK_URL = "https://discord.com/api/webhooks/1335930745843089458/AYK-0btOe8vN-LE9ugVV15aDKi_XTNaNYij4iZS021qzzt6RPGt9TkHwQwzjCLP0arOB"

redis = Redis(url="https://hopeful-primate-11670.upstash.io", token="AS2WAAIjcDEwMzE0MjVhY2JkNDc0MzFjYTQxZGY4MDFmYzJhNGY2ZXAxMA")

# 📌 一時ファイル保存フォルダ
UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def generate_hash():
    """8桁の一意なランダムハッシュを生成"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def upload_to_discord(file_path, is_public):
    """画像をDiscordにアップロードし、CDNのURLを取得"""
    webhook_url = PUBLIC_WEBHOOK_URL if is_public else PRIVATE_WEBHOOK_URL
    files = {'file': open(file_path, 'rb')}
    response = requests.post(webhook_url, files=files)
    files['file'].close()
    
    if response.status_code == 200:
        json_resp = response.json()
        return json_resp['attachments'][0]['url']
    return None

import requests

def send_text_to_discord(text, is_public):
    """Discordに文字だけを送信"""
    webhook_url = PUBLIC_WEBHOOK_URL if is_public else PRIVATE_WEBHOOK_URL
    
    data = {
        'content': f"```{text}```"  # 送信したいテキスト
    }
    
    response = requests.post(webhook_url, json=data)
    
    if response.status_code == 200:
        return "メッセージ送信成功"
    else:
        return "メッセージ送信に失敗しました"
        
def allowed_file(filename):
    # 拡張子を小文字にして取得
    ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.mp4', '.mov', '.avi', '.mkv', '.mp3', '.wav', '.flac'}
    ext = os.path.splitext(filename)[1].lower()
    print(ext)
    return ext in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET"])
def index():
    """アップロードページを表示"""
    return render_template("upload.html")

@app.route("/upload", methods=["POST"])
def upload():
    """画像をアップロードし、Discord → Pastebin に保存"""
    if "file" not in request.files:
        return "ファイルが選択されていません"
    
    file = request.files["file"]
    if file.filename == "":
        return "ファイルがありません"
    
    # ✅ 公開設定を取得
    is_public = request.form.get("visibility") == "public"
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only images are allowed.'}), 400
    # ✅ ファイルを保存
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    hash = generate_hash()
    
    cdn_url = upload_to_discord(file_path, is_public)
    os.remove(file_path)  # アップロード後、ローカルから削除
    redis.set(hash, cdn_url)
    
    if cdn_url:
        send_text_to_discord(f'https://soliup.kei1215.com/{hash}', is_public)
        if cdn_url:
            return f"アップロード成功！画像URL: <a href='https://soliup.kei1215.com/{hash}'>https://soliup.kei1215.com/{hash}</a>"
        else:
            return "Pastebin への保存に失敗しました"
    
    return "アップロードに失敗しました"

@app.route("/<hash_value>", methods=["GET"])
def image_view(hash_value):
    """ハッシュ値に対応する画像を取得し表示"""
    url = redis.get(hash_value)
    
    if url:
        image_data = requests.get(url).content  # URLから画像データを取得
        
        # ファイルの拡張子からMIMEタイプを取得
        mime_type, _ = mimetypes.guess_type(url.split('?')[0])
        print(mime_type)
        if not mime_type:
            mime_type = "application/octet-stream"  # 不明な場合は汎用バイナリデータ
            
        return Response(image_data, mimetype=mime_type)
    
    return "画像が見つかりません", 404

if __name__ == "__main__":
    app.run(debug=True)
