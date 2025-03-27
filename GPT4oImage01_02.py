import base64
import os
import threading
import time
from datetime import datetime

import cv2
import requests

# 出力ディレクトリの作成
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# Webカメラから映像をキャプチャ
cap = cv2.VideoCapture(0)

# APIと通信設定
API_KEY = '******************************************************************************'
API_URL = "https://api.openai.com/v1/chat/completions"
MODEL_NAME = 'gpt-4o'

interval = 10
capture_duration = 1


def show_image():
    while True:
        # フレームをキャプチャ
        ret, frame = cap.read()

        # フレームの読み取りが成功したかどうかをチェック
        if not ret:
            # print("フレームの取得に失敗しました。")
            continue

        # 画像をウィンドウに表示
        cv2.imshow('Web camera', frame)

        # 'q'キーが押されたらループから抜ける
        if cv2.waitKey(1) == ord('q'):
            break


def capture_images():
    while True:
        filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(output_dir, filename)

        ret, frame = cap.read()

        if ret:
            cv2.imwrite(filepath, frame)
            time.sleep(capture_duration)
        else:
            continue


def run_curl_command(start_time, headers, payload):
    
    response = requests.post(API_URL, headers=headers, json=payload)

    print(response.json()['choices'][0]['message']['content'])
    elapsed_time = time.time() - start_time
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] (処理時間: {elapsed_time:.2f}秒)")


def send_images_to_api():

    last_time = time.time()

    while True:
        start_time = time.time()
        
        # 最新の10枚の画像を取得
        with threading.Lock():
            image = sorted(os.listdir(output_dir))[-1]
            image_path = os.path.join(output_dir, image)
        
        system_prompt = 'このシステムは画像の内容を分析して、その説明を生成します。分析結果を日本語で回答します。'
        user_prompt = 'この画像は、屋内に設置した防犯カメラで撮影した画像です。人物の動作が危険だと思ったら警告を出してください。'
        
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            data_uri = f'data:image/jpeg;base64,{encoded_image}'
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": data_uri}}
            ]}
        ]
        
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "max_tokens": 1000
        }

        headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            }
        
        thread = threading.Thread(target=run_curl_command, args=(start_time, headers, payload))
        thread.start()
        
        # 次のキャプチャまでの正確な待機時間を計算
        elapsed_time = time.time() - start_time
        sleep_duration = max(0, interval - elapsed_time)
        last_time = start_time
        if sleep_duration >= 0.0:
            time.sleep(sleep_duration)  # 次のキャプチャまで待機


# 画像キャプチャスレッド
capture_thread = threading.Thread(target=capture_images)
capture_thread.start()

# API送信スレッドのスケジューリング
schedule_thread = threading.Thread(target=send_images_to_api)
schedule_thread.start()

# 画像表示
show_image()

# スレッドの終了を待機
capture_thread.join()
schedule_thread.join()

# Webカメラのリリース
cap.release()

