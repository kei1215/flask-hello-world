from flask import Flask, request, render_template, redirect, url_for, Response, jsonify
import os
import random
import string
import requests
import mimetypes

app = Flask(__name__)

# 📌 Discord Webhook URLs (公開枠 & 限定公開枠)
PUBLIC_WEBHOOK_URL = "https://discord.com/api/webhooks/1335903672130994216/nquebBIPEnslaSsiGdHXBYQpmMsKIhxzt0eGjIuiyysgljKVZSpJZiGiO1mtYSLy-KbA"
PRIVATE_WEBHOOK_URL = "YOUR_PRIVATE_DISCORD_WEBHOOK"

# 📌 Pastebin APIキー
PASTEBIN_API_KEY = "iORBwgh6pDEr9UBFgH0pyPHV20sjwJZP"
PASTEBIN_URL = "https://pastebin.com/api/api_post.php"

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
        
def save_to_pastebin(cdn_url):
    """Pastebinに画像URLとハッシュを保存し、そのURLを返す"""
    data = {
        "api_dev_key": PASTEBIN_API_KEY,
        "api_option": "paste",
        "api_paste_code": f"{cdn_url}",
        "api_paste_private": "1",  # 0=public, 1=unlisted, 2=private
        "api_paste_format": "text"
    }
    
    response = requests.post(PASTEBIN_URL, data=data)
    
    if response.status_code == 200:
        return response.text  # PastebinのURLが返る
    else:
        return None

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
    ALLOWED_MIME_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/bmp']
    mime_type, _ = mimetypes.guess_type(file.filename)
    
    if mime_type not in ALLOWED_MIME_TYPES:
        return jsonify({'error': 'Invalid file type. Only images are allowed.'}), 400
    # ✅ ファイルを保存
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    
    # ✅ Discord にアップロードして CDN URL を取得
    cdn_url = upload_to_discord(file_path, is_public)
    os.remove(file_path)  # アップロード後、ローカルから削除
    
    if cdn_url:
        pastebin_url = save_to_pastebin(cdn_url)
        photo_url = pastebin_url.replace("https://pastebin.com/", "https://photo.kei1215.net/")
        send_text_to_discord(photo_url, is_public)
        if pastebin_url:
            return f"アップロード成功！画像URL: <a href='{photo_url}'>{photo_url}</a>"
        else:
            return "Pastebin への保存に失敗しました"
    
    return "アップロードに失敗しました"

@app.route("/<hash_value>", methods=["GET"])
def image_view(hash_value):
    """ハッシュ値に対応する画像を取得し表示"""
    pastebin_url = f"https://pastebin.com/raw/{hash_value}"
    response = requests.get(pastebin_url)
    
    if response.status_code == 200:
        image_data = requests.get(response.text).content  # URLから画像データを取得
        return Response(image_data, mimetype='image/png')
    
    return "画像が見つかりません", 404

if __name__ == "__main__":
    app.run(debug=True)
