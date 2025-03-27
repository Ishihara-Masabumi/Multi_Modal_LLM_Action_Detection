import openai
import speech_recognition as sr
import pyttsx3

# OpenAI APIキーを設定
openai.api_key = 'YOUR_OPENAI_API_KEY'

# 音声認識の初期化
recognizer = sr.Recognizer()
microphone = sr.Microphone()

# テキスト読み上げの初期化
engine = pyttsx3.init()

# GPT-4oへのクエリ関数
def query_gpt4o(text):
    response = openai.Completion.create(
        engine="gpt-4o",
        prompt=text,
        max_tokens=150
    )
    return response.choices[0].text.strip()

# 音声認識とGPT-4oとのやり取り
def recognize_and_respond():
    with microphone as source:
        print("話しかけてください...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
        
    try:
        text = recognizer.recognize_google(audio, language="ja-JP")
        print(f"認識結果: {text}")
        
        response_text = query_gpt4o(text)
        print(f"GPT-4oの回答: {response_text}")
        
        engine.say(response_text)
        engine.runAndWait()
        
    except sr.UnknownValueError:
        print("音声を認識できませんでした。もう一度話しかけてください。")
    except sr.RequestError as e:
        print(f"音声認識サービスにエラーが発生しました: {e}")

if __name__ == "__main__":
    while True:
        recognize_and_respond()
