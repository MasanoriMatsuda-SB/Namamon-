import streamlit as st
import openai
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime
import folium
from streamlit_folium import st_folium

# APIキー
openai.api_key = st.secrets["OpenAI_API"]["Key"]
weather_api_key = st.secrets["OpenWeatherMap_API"]["Key"]
google_translate_api_key = st.secrets["Google_Translate_API"]["Key"]
google_api_key = st.secrets["GoogleMaps_API"]["Key"]

# GBIF API URL
gbif_api_url = "https://api.gbif.org/v1/species/search?q="

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

# Google翻訳APIを使用して日本語から英語に翻訳する関数
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

content_kind_of = {
    "ポケモン博士": "ポケモン図鑑風に動植物を紹介してください。例文を参考にお願いします。例文：森の中で仲間と暮らす。ほっぺたの両側にある電気袋に電気を溜める。",
    
    "小学校の先生": "小学生向けに、わかりやすくて楽しいトーンで動植物を紹介してください。子供たちが興味を持つように、日常生活に結びつけた簡単な豆知識や観察のコツも教えてください。",
    
    "次々探索したくさせる先生": "小学生向けに、わかりやすく楽しいトーンで動植物を紹介してください。さらに、他の動植物も探索したくなるように関連する他の動植物の名前と見つけ方のコツを合わせて提案してください",
    
    "さかなクン": "さかなクンの明るく親しみやすいトーンで、動植物を紹介してください。冒頭に『ギョギョギョ～！』をつけて、子供たちがワクワクするような楽しい表現や擬音を交えながら説明してください。",
    
    "レア度を5段階評価する動植物マニア": "動物の希少性を5段階で評価する動植物マニアとして、動植物を紹介してください。冒頭に5段階の評価結果を伝え、改行して希少性の背景や動植物の特徴を説明してください",
}

# OpenAIを使用して説明文を生成する関数
def generate_description(animal_name, description_style, max_length):
    prompt = f"次の動物の説明文を、{description_style}動物名は{animal_name}です。{max_length}文字以内でお願いします。"
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたはポケモン図鑑のスタイルで動物の説明を作成するAIアシスタントです。"},
            {"role": "user", "content": prompt}
        ]
    )
    output_content = response.choices[0].message.content.strip()
    return output_content

# 緯度と経度から天気情報を取得する関数
def get_weather(lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={weather_api_key}&units=metric&lang=ja"
    response = requests.get(url)
    return response.json()

# 緯度と経度から住所を取得する関数
def get_address(lat, lon):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={google_api_key}&language=ja"
    response = requests.get(url)
    return response.json()

# Streamlitアプリのレイアウト
st.set_page_config(page_title="Namamon図鑑", layout="wide")
st.title("Namamon図鑑")

# サイドバーに入力フィールドと保存ボタンを配置
with st.sidebar:
    st.header("図鑑情報の入力")
    animal_name = st.text_input("動物名")
    capture_date = st.date_input("捕獲日")
    capture_time = st.time_input("捕獲時刻")
    uploaded_file = st.file_uploader("動物の画像をアップロード", type=["png", "jpg", "jpeg"])
    content_kind_of_to_gpt = st.sidebar.selectbox("説明する人物",options=content_kind_of)
    content_maxStr_to_gpt = str(st.sidebar.slider('説明文字数の上限', 100,200,300))


    # 地図を表示して捕獲場所を選択
    m = folium.Map(location=[35.0, 135.0], zoom_start=5)
    m.add_child(folium.LatLngPopup())
    st.write("地図をクリックして地点を選択してください。")
    map_data = st_folium(m, width=280, height=200)

    capture_location_value = None
    weather = None
    temperature = None
    clicked_lat, clicked_lon = 35.0, 135.0

    if map_data is not None and 'last_clicked' in map_data and map_data['last_clicked'] is not None:
        clicked_lat = map_data['last_clicked']['lat']
        clicked_lon = map_data['last_clicked']['lng']
        st.write(f"クリックされた地点の緯度: {clicked_lat}, 経度: {clicked_lon}")
        address_data = get_address(clicked_lat, clicked_lon)
        if address_data['status'] == 'OK':
            capture_location_value = address_data['results'][0]['formatted_address']
            st.text_input("捕獲場所", value=capture_location_value)
            st.write(f"住所: {capture_location_value}")
            
            # 天気情報を取得
            weather_data = get_weather(clicked_lat, clicked_lon)
            if weather_data and 'weather' in weather_data:
                weather = weather_data['weather'][0]['description']
                temperature = weather_data['main']['temp']
                st.write(f"地点の天気: {weather}")
                st.write(f"気温: {temperature}°C")
            else:
                st.error("天気情報の取得に失敗しました。")
        else:
            st.write("住所の取得に失敗しました。")

    if st.button("図鑑を作成"):
        if animal_name and capture_location_value and capture_date and capture_time and uploaded_file:
            description = generate_description(animal_name, content_kind_of[content_kind_of_to_gpt], content_maxStr_to_gpt)
            scientific_name = get_scientific_name(animal_name)
            img_bytes = uploaded_file.getvalue()
            full_datetime = datetime.combine(capture_date, capture_time)

            st.session_state["zukan_entry"] = {
                "animal_name": animal_name,
                "scientific_name": scientific_name,
                "capture_location": capture_location_value,
                "capture_date": full_datetime.strftime('%Y-%m-%d %H:%M'),
                "weather": weather,
                "temperature": temperature,
                "description": description,
                "image": img_bytes.hex(),
                "lat": clicked_lat,
                "lon": clicked_lon
            }

            st.session_state["zukan_created"] = True
        else:
            st.error("全てのフィールドを入力し、画像をアップロードしてください。")

    # 保存ボタンを追加
    if "zukan_created" in st.session_state and st.session_state["zukan_created"]:
        if st.button("この図鑑を保存"):
            if "zukan_data" not in st.session_state:
                st.session_state["zukan_data"] = []
            st.session_state["zukan_data"].append(st.session_state["zukan_entry"])
            st.success("図鑑が保存されました！")
            st.session_state["zukan_created"] = False

# メインコンテンツのレイアウト
tab1, tab2 = st.tabs(["図鑑作成", "保存された図鑑一覧"])
with tab1:
    if "zukan_created" in st.session_state and st.session_state["zukan_created"]:
        entry = st.session_state["zukan_entry"]
        
        st.subheader(f"名前: {entry['animal_name']}")
        st.subheader(f"学名: {entry['scientific_name']}")
        st.image(BytesIO(bytes.fromhex(entry["image"])), caption=entry['animal_name'], use_column_width=True)
        st.subheader("捕獲情報")
        st.write(f"場所: {entry['capture_location']}")
        st.write(f"日時: {entry['capture_date']}")
        st.write(f"天気: {entry['weather']}")
        st.write(f"気温: {entry['temperature']}°C")
        st.subheader("説明")
        st.write(entry['description'])

        # 住所情報に基づいてマップを表示し、「分布」のタイトルを付ける
        st.subheader("分布")
        map_display = folium.Map(location=[entry['lat'], entry['lon']], zoom_start=10)
        folium.Marker(location=[entry['lat'], entry['lon']], popup=entry['capture_location']).add_to(map_display)
        st_folium(map_display, width=700, height=500)
    else:
        st.write("サイドバーから図鑑情報を入力し、図鑑を作成してください。")

with tab2:
    st.subheader("保存された図鑑一覧")
    if "zukan_data" in st.session_state:
        for idx, entry in enumerate(st.session_state["zukan_data"]):
            st.subheader(f"図鑑エントリー {idx + 1}")
            st.write(f"名前: {entry['animal_name']}")
            st.write(f"学名: {entry['scientific_name']}")
            st.image(BytesIO(bytes.fromhex(entry["image"])), caption=entry['animal_name'], use_column_width=True)
            st.write(f"場所: {entry['capture_location']}")
            st.write(f"日時: {entry['capture_date']}")
            st.write(f"天気: {entry['weather']}")
            st.write(f"気温: {entry['temperature']}°C")
            st.write(f"説明: {entry['description']}")

            # 保存された図鑑の場所を示すマップを表示し、「分布」のタイトルを付ける
            st.subheader("分布")
            map_display = folium.Map(location=[entry['lat'], entry['lon']], zoom_start=10)
            folium.Marker(location=[entry['lat'], entry['lon']], popup=entry['capture_location']).add_to(map_display)
            st_folium(map_display, width=700, height=500)
    else:
        st.write("保存された図鑑はありません。")
