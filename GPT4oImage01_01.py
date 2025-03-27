import base64
import json
import os
import subprocess
import threading
from datetime import datetime
from time import sleep, time

import cv2

# 出力ディレクトリの作成
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# Webカメラから映像をキャプチャ
cap = cv2.VideoCapture(0)


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
        ret, frame = cap.read()
        if not ret:
            break
        
        # 512x512にリサイズ
        frame_resized = cv2.resize(frame, (512, 512))
        
        # ファイル名の生成
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S.%f")[:-3]
        filename = f"{output_dir}/image_{timestamp}.jpg"
        
        # 画像を保存
        cv2.imwrite(filename, frame_resized)
        
        # 0.5秒待機
        sleep(0.5)

def run_curl_command(start_time):
    result = subprocess.run(
        ["curl", "https://api.openai.com/v1/chat/completions",
         "-H", "Content-Type: application/json",
         "-H", "Authorization: Bearer *****************************************************",
         "-d", "@payload.json"],
        capture_output=True, text=True)
    
    response = result.stdout
    elapsed_time = time() - start_time
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] (経過時間: {elapsed_time:.2f}秒)")
    try:
        response_json = json.loads(response)
        if "choices" in response_json:
            message_content = response_json["choices"][0]["message"]["content"]
            print(f"Response Content: {message_content}")
    except json.JSONDecodeError:
        print("Failed to decode JSON response")

def send_images_to_api():
    while True:
        start_time = time()
        
        # 最新の10枚の画像を取得
        with threading.Lock():
            images = sorted(os.listdir(output_dir))[-10:]
            image_paths = [os.path.join(output_dir, image) for image in images]
        
        if len(image_paths) < 10:
            sleep(5)
            continue
        
        system_prompt = 'このシステムは画像の内容を分析して、その説明を生成します。分析結果を日本語で回答します。'
        user_prompt = 'この画像は、屋内に設置した防犯カメラで撮影した画像です。人物の動作が危険だと思ったら警告を出してください。'
        
        data_uris = []
        for image_path in image_paths:
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                data_uri = f'data:image/jpeg;base64,{encoded_image}'
                data_uris.append(data_uri)
                break
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": user_prompt},
                *[{"type": "image_url", "image_url": {"url": data_uri}} for data_uri in data_uris]
            ]}
        ]
        
        payload = {
            "model": "gpt-4o",
            "messages": messages,
            "max_tokens": 1000
        }
        
        with open("payload.json", "w") as json_file:
            json.dump(payload, json_file)
        
        thread = threading.Thread(target=run_curl_command, args=(start_time,))
        thread.start()
        
        sleep(10)  # 5秒待機

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

