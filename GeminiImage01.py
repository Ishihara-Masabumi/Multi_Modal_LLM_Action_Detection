import os
import threading
import time
from datetime import datetime

import cv2
import google.generativeai as genai

# APIと通信設定
API_KEY = "AIzaSyC4-EM1rg2H6nzd56IsqUgz5YWc44j3HgI"
API_URL = "https://api.example.com/gemini"
MODEL_NAME = 'gemini-1.5-flash'
genai.configure(api_key=API_KEY)

# 出力フォルダの設定
output_folder = "images"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# ビデオキャプチャの設定
cap = cv2.VideoCapture(0)
# cap.set(cv2.CAP_PROP_FRAME_WIDTH, 512)
# cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 512)
interval = 10
capture_duration = 1

lock = threading.Lock()


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


def capture_image():
    while True:
        filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(output_folder, filename)
        # out = cv2.VideoWriter(filepath, cv2.VideoWriter_fourcc(*'mp4v'), frame_rate, (640, 480))

        # 10秒間ビデオを記録
        # start_time = time.time()
        while True:
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(filepath, frame)
                time.sleep(capture_duration)
            else:
                continue


def run_request_command(start_time, image_path):
    # ビデオのアップロード
    uploaded_image = genai.upload_file(path=image_path)
    print("Completed upload:", uploaded_image.uri)
    
    # ビデオが処理中
    while uploaded_image.state.name == "PROCESSING":
        print("Image is processed.")
        time.sleep(0.1)
        uploaded_image = genai.get_file(uploaded_image.name)
        # print(f"uploaded_video.name:{uploaded_video.name}")
    
    print(uploaded_image.state.name)
    if uploaded_image.state.name == "FAILED":  # ビデオ取得失敗
        return
    elif uploaded_image.state.name == "ACTIVE":  # ビデオ取得成功
        model = genai.GenerativeModel(MODEL_NAME)
        prompt = """
    このシステムは画像の内容を分析して、その説明を生成してください。分析結果を日本語で回答してください。
    この画像は、屋内に設置した防犯カメラで撮影した画像です。人物の動作が危険だと思ったら警告を出してください。
    """
        content = [prompt, uploaded_image]
        response = model.generate_content(content)
        elapsed_time = time.time() - start_time
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] (処理時間: {elapsed_time:.2f}秒)")
        print(response.candidates[0].content.parts[0].text)
    else:
        return


def send_image_to_api():
    while True:
        start_time = time.time()
        with lock:
            images = sorted(os.listdir(output_folder))
            if len(images) < 2:
                continue
            else:
                image = images[-2]
                image_path = os.path.join(output_folder, image)

                # 新しいスレッドでAPIリクエストを実行
                thread = threading.Thread(target=run_request_command, args=(start_time, image_path))
                thread.start()

        # 次のキャプチャまでの正確な待機時間を計算
        elapsed_time = time.time() - start_time
        sleep_duration = max(0, interval - elapsed_time)
        if sleep_duration >= 0.0:
            time.sleep(sleep_duration)  # 次のキャプチャまで待機


# 画像表示スレッド
# capture_thread = threading.Thread(target=show_video)
# capture_thread.start()

# 画像キャプチャスレッド
capture_thread = threading.Thread(target=capture_image)
capture_thread.start()

# API送信スレッドのスケジューリング
schedule_thread = threading.Thread(target=send_image_to_api)
schedule_thread.start()

# 画像表示
show_image()

# スレッドの終了を待機
capture_thread.join()
schedule_thread.join()

# Webカメラのリリース
cap.release()

