from flask import Flask, request, render_template, redirect, url_for
import os
import random
import string
import requests

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

def save_to_pastebin(hash_value, cdn_url):
    """Pastebinに画像URLとハッシュを保存し、そのURLを返す"""
    data = {
        "api_dev_key": PASTEBIN_API_KEY,
        "api_option": "paste",
        "api_paste_code": f"{hash_value}: {cdn_url}",
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

import json

def upload_to_discord(file_path, is_public):
    """画像をDiscordにアップロードし、CDNのURLを取得"""
    webhook_url = PUBLIC_WEBHOOK_URL if is_public else PRIVATE_WEBHOOK_URL
    with open(file_path, 'rb') as f:
        files = {'file': f}
        # 画像をアップロード
        response = requests.post(webhook_url, files=files)

    if response.status_code == 200:
        try:
            json_resp = response.json()
            # 画像URLを取得
            image_url = json_resp['attachments'][0]['url']
            # リンクと一緒にメッセージを送信
            message_data = {
                "content": f"画像がアップロードされました！\nリンク: https://photo.kei1215.net/{unique_hash}",
                "embeds": [{
                    "image": {
                        "url": image_url
                    }
                }]
            }
            # メッセージをWebhookで送信
            response_message = requests.post(webhook_url, json=message_data)
            if response_message.status_code == 204:
                return image_url  # 画像URLを返す
        except KeyError:
            return "DiscordのレスポンスにURLが含まれていません"
    return None


@app.route("/<hash_value>", methods=["GET"])
def image_view(hash_value):
    """ハッシュ値に対応する画像を取得し表示"""
    pastebin_url = f"https://pastebin.com/raw/{hash_value}"
    response = requests.get(pastebin_url)
    
    if response.status_code == 200:
        data = response.text.strip().split(": ")
        if len(data) == 2:
            _, image_url = data
            return f'<img src="{image_url}" alt="Uploaded Image">'
    
    return "画像が見つかりません", 404

if __name__ == "__main__":
    app.run(debug=True)
