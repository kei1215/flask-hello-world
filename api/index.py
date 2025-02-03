from flask import Flask, request, render_template, redirect, url_for
import os
import random
import string
import requests

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Discord Webhook URLs (公開枠 & 限定公開枠)
PUBLIC_WEBHOOK_URL = "YOUR_PUBLIC_DISCORD_WEBHOOK"
PRIVATE_WEBHOOK_URL = "YOUR_PRIVATE_DISCORD_WEBHOOK"

# 画像データを保存する辞書 (Hash: URL)
uploaded_images = {}

def generate_hash():
    """8桁のランダムなハッシュを生成"""
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

@app.route('/', methods=['GET'])
def index():
    """保存された画像のリストを表示"""
    return render_template('index.html', images=uploaded_images)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "ファイルが選択されていません"
        file = request.files['file']
        if file.filename == '':
            return "ファイルがありません"
        
        is_public = request.form.get('visibility') == 'public'
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        
        cdn_url = upload_to_discord(file_path, is_public)
        os.remove(file_path)  # アップロード後ローカルから削除
        
        if cdn_url:
            unique_hash = generate_hash()
            while unique_hash in uploaded_images:
                unique_hash = generate_hash()
            uploaded_images[unique_hash] = cdn_url
            return redirect(url_for('image_view', hash=unique_hash))
        else:
            return "アップロードに失敗しました"
    
    return render_template('upload.html')

@app.route('/<hash>', methods=['GET'])
def image_view(hash):
    """ハッシュに対応する画像を表示"""
    if hash in uploaded_images:
        return f'<img src="{uploaded_images[hash]}" alt="Uploaded Image">'
    return "画像が見つかりません", 404

if __name__ == '__main__':
    app.run(debug=True)
