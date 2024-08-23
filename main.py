import streamlit as st
import openai
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime
import json

# OpenAI API Key
openai.api_key = st.secrets["OpenAI_API"]["Key"]

# OpenWeatherMap API Key
weather_api_key = st.secrets["OpenWeatherMap_API"]["Key"]

# Google Translate API Key
google_translate_api_key = st.secrets["Google_Translate_API"]["Key"]

# GBIF API URL
gbif_api_url = "https://api.gbif.org/v1/species/search?q="

# 天気情報を取得する関数
def get_weather(date, location):
    try:
        geocode_url = f'http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={weather_api_key}'
        geocode_response = requests.get(geocode_url)
        geocode_data = geocode_response.json()

        if len(geocode_data) == 0:
            return "指定された場所の情報が見つかりませんでした"

        lat = geocode_data[0]['lat']
        lon = geocode_data[0]['lon']
        
        weather_url = f'https://api.openweathermap.org/data/2.5/onecall/timemachine?lat={lat}&lon={lon}&dt={int(datetime.strptime(date, "%Y-%m-%d").timestamp())}&appid={weather_api_key}&lang=ja&units=metric'
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()

        if 'current' in weather_data:
            return weather_data['current']['weather'][0]['description']
        else:
            return "天気情報が見つかりませんでした"

    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

# 説明文を生成する関数
def generate_description(animal_name):
    prompt = f"以下の動物の説明文を、ポケモン図鑑風に作成してください。動物名は{animal_name}です。"
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "あなたはポケモン図鑑のスタイルで動物の説明を作成するAIアシスタントです。"},
            {"role": "user", "content": prompt}
        ]
    )
    output_content = response.choices[0].message.content.strip()
    return output_content

# 日本語名を英語名に翻訳する関数
def translate_to_english(japanese_name):
    translate_url = f"https://translation.googleapis.com/language/translate/v2?key={google_translate_api_key}"
    params = {
        'q': japanese_name,
        'source': 'ja',
        'target': 'en',
        'format': 'text'
    }
    response = requests.post(translate_url, data=params)
    data = response.json()
    if 'data' in data and 'translations' in data['data']:
        return data['data']['translations'][0]['translatedText']
    else:
        return "翻訳できませんでした"

# 学名を取得する関数
def get_scientific_name(animal_name):
    try:
        english_name = translate_to_english(animal_name)
        if english_name == "翻訳できませんでした":
            return "学名が見つかりませんでした"
        
        response = requests.get(gbif_api_url + english_name)
        data = response.json()
        if data['results']:
            return data['results'][0]['scientificName']
        else:
            return "学名が見つかりませんでした"
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

# Session Stateを使って図鑑データを保存する関数
def save_to_session_state(data):
    if "zukan_data" not in st.session_state:
        st.session_state["zukan_data"] = []
    st.session_state["zukan_data"].append(data)

# Streamlitアプリのレイアウト
st.set_page_config(page_title="Namamon図鑑", layout="wide")
st.title("Namamon図鑑")

# サイドバーに入力フィールドを移動
with st.sidebar:
    st.header("図鑑情報の入力")
    animal_name = st.text_input("動物名")
    capture_location = st.text_input("捕獲場所")
    capture_date = st.date_input("捕獲日")
    capture_time = st.time_input("捕獲時刻")
    uploaded_file = st.file_uploader("動物の画像をアップロード", type=["png", "jpg", "jpeg"])

    if st.button("図鑑を作成"):
        if animal_name and capture_location and capture_date and capture_time and uploaded_file:
            # 天気情報を取得
            full_datetime = datetime.combine(capture_date, capture_time)
            weather = get_weather(capture_date.strftime('%Y-%m-%d'), capture_location)
            
            # 説明文を生成
            description = generate_description(animal_name)

            # 学名を取得
            scientific_name = get_scientific_name(animal_name)
            
            # 画像をバイトデータとして保存
            img_bytes = uploaded_file.getvalue()

            # 図鑑データを保存（セッションに保存しておく）
            zukan_entry = {
                "animal_name": animal_name,
                "scientific_name": scientific_name,
                "capture_location": capture_location,
                "capture_date": full_datetime.strftime('%Y-%m-%d %H:%M'),
                "weather": weather,
                "description": description,
                "image": img_bytes.hex()  # 画像を16進数文字列に変換して保存
            }
            save_to_session_state(zukan_entry)

            # 図鑑の内容を表示
            st.session_state["zukan_created"] = True
        else:
            st.error("全てのフィールドを入力し、画像をアップロードしてください。")

# メインコンテンツのレイアウト
tab1, tab2 = st.tabs(["図鑑作成", "保存された図鑑一覧"])

with tab1:
    if "zukan_created" in st.session_state and st.session_state["zukan_created"]:
        entry = st.session_state["zukan_data"][-1]
        
        st.subheader(f"名前: {entry['animal_name']}")
        st.subheader(f"学名: {entry['scientific_name']}")
        st.image(BytesIO(bytes.fromhex(entry["image"])), caption=entry['animal_name'], use_column_width=True)
        st.subheader("捕獲情報")
        st.write(f"場所: {entry['capture_location']}")
        st.write(f"日時: {entry['capture_date']}")
        st.write(f"天気: {entry['weather']}")
        st.subheader("説明")
        st.write(entry['description'])

        if st.button("図鑑を保存"):
            st.success("図鑑が保存されました！")
            st.session_state["zukan_created"] = False
    else:
        st.write("サイドバーから図鑑情報を入力し、図鑑を作成してください。")

with tab2:
    st.subheader("保存された図鑑一覧")
    if "zukan_data" in st.session_state:
        for entry in st.session_state["zukan_data"]:
            st.subheader(f"名前: {entry['animal_name']}")
            st.subheader(f"学名: {entry['scientific_name']}")
            st.image(BytesIO(bytes.fromhex(entry["image"])), caption=entry['animal_name'], use_column_width=True)
            st.write(f"場所: {entry['capture_location']}")
            st.write(f"日時: {entry['capture_date']}")
            st.write(f"天気: {entry['weather']}")
            st.write("説明:")
            st.write(entry['description'])
            st.write("---")
    else:
        st.write("保存された図鑑がまだありません。")
