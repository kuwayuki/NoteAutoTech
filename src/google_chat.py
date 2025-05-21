import requests
from dotenv import load_dotenv
import os

load_dotenv()


def send_to_google_chat(text):
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    try:
        response = requests.post(
            WEBHOOK_URL,
            json={"text": text},
            headers={"Content-Type": "application/json; charset=UTF-8"},
        )
        if response.status_code == 200:
            print("メッセージが正常に送信されました。")
        else:
            print(f"送信エラー: {response.status_code}, {response.text}")
    except Exception as e:
        print("送信エラー:", e)
