import cv2
import threading
import time
from datetime import datetime
import os
import requests
import google.generativeai as genai
from queue import Queue

# APIと通信設定
API_KEY = "AIzaSyC4-EM1rg2H6nzd56IsqUgz5YWc44j3HgI"  # 実際のAPIキーを安全に管理してください
API_URL = "https://api.example.com/gemini"
MODEL_NAME = 'gemini-1.5-flash'
genai.configure(api_key=API_KEY)

# 出力フォルダの設定
output_folder = "output"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# ビデオキャプチャの設定
cap = cv2.VideoCapture(0)
frame_rate = 2
capture_duration = 5

lock = threading.Lock()
display_queue = Queue()
capture_queue = Queue()

def frame_reader():
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # フレームを表示用と保存用のキューに入れる
        display_queue.put(frame)
        capture_queue.put(frame)
        time.sleep(1 / frame_rate)

def show_video():
    delay = 1  # ミリ秒単位の遅延
    while True:
        if not display_queue.empty():
            frame = display_queue.get()
            # 画像をウィンドウに表示
            cv2.imshow('Web camera', frame)
            # 'q'キーが押されたらループから抜ける
            if cv2.waitKey(delay) & 0xFF == ord('q'):
                break
        else:
            time.sleep(0.01)

def capture_video():
    while True:
        filename = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = os.path.join(output_folder, filename)
        
        # フレームサイズを取得
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # フレームサイズが取得できない場合、最初のフレームから取得
        if frame_width == 0 or frame_height == 0:
            if not capture_queue.empty():
                frame = capture_queue.queue[0]
                frame_height, frame_width = frame.shape[:2]
            else:
                time.sleep(0.1)
                continue
        
        out = cv2.VideoWriter(filepath, cv2.VideoWriter_fourcc(*'mp4v'), frame_rate, (frame_width, frame_height))

        # 5秒間ビデオを記録
        start_time = time.time()
        frames_captured = 0
        while (time.time() - start_time) < capture_duration:
            if not capture_queue.empty():
                frame = capture_queue.get()
                out.write(frame)
                frames_captured += 1
            else:
                time.sleep(0.01)
        out.release()
        elapsed_time = time.time() - start_time
        print(f"録画時間: {elapsed_time:.2f}秒, フレーム数: {frames_captured}")

        # 次のキャプチャまでの待機（必要なら）
        time.sleep(0.1)

def run_request_command(start_time, video_path):
    # ビデオのアップロード
    uploaded_video = genai.upload_file(path=video_path)
    print("Completed upload:", uploaded_video.uri)
    
    # ビデオが処理中
    while uploaded_video.state.name == "PROCESSING":
        print("Video is processed.")
        time.sleep(0.1)
        uploaded_video = genai.get_file(uploaded_video.name)
    
    print(uploaded_video.state.name)
    if uploaded_video.state.name == "FAILED":  # ビデオ取得失敗
        return
    elif uploaded_video.state.name == "ACTIVE":  # ビデオ取得成功
        model = genai.GenerativeModel(MODEL_NAME)
        prompt = """
    この動画に映っている人物の行動の説明をしてください。
    この人物の行動に、何か不審な行動や危険な行動や暴力的な行動が認められたら、直ちに「警告！」を表示してください。
    """
        content = [prompt, uploaded_video]
        response = model.generate_content(content)
        elapsed_time = time.time() - start_time
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] (処理時間: {elapsed_time:.2f}秒)")
        print(response.candidates[0].content.parts[0].text)
    else:
        return

def send_video_to_api():
    while True:
        start_time = time.time()
        with lock:
            videos = sorted(os.listdir(output_folder))
            if len(videos) < 2:
                time.sleep(0.1)
                continue
            else:
                video = videos[-2]
                video_path = os.path.join(output_folder, video)

                # 新しいスレッドでAPIリクエストを実行
                thread = threading.Thread(target=run_request_command, args=(start_time, video_path))
                thread.start()

        # 次のキャプチャまでの待機
        time.sleep(capture_duration)

# フレーム読み取りスレッド
frame_reader_thread = threading.Thread(target=frame_reader)
frame_reader_thread.start()

# 画像表示スレッド
show_thread = threading.Thread(target=show_video)
show_thread.start()

# 画像キャプチャスレッド
capture_thread = threading.Thread(target=capture_video)
capture_thread.start()

# API送信スレッドのスケジューリング
schedule_thread = threading.Thread(target=send_video_to_api)
schedule_thread.start()

# スレッドの終了を待機
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass

frame_reader_thread.join()
show_thread.join()
capture_thread.join()
schedule_thread.join()

# Webカメラのリリース
cap.release()
cv2.destroyAllWindows()
