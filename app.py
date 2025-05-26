import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium import CircleMarker
from streamlit_folium import st_folium

# タイトル
st.set_page_config(page_title="Evacuation Capacity Visualizer", layout="wide")
st.title("Evacuation Capacity Visualizer（避難所収容状況可視化）")

# GeoJSON 読み込み
GEOJSON_PATH = "hinanjyo１.geojson"
gdf = gpd.read_file(GEOJSON_PATH)

# 必須カラム名
ID_COL = "name"  # GeoJSON側のIDや名前カラム名
CAP_COL = "capacity"  # GeoJSON側の収容人数カラム名

# CSVの読み込み
st.sidebar.header("収容人数CSVをアップロード")
uploaded_csv = st.sidebar.file_uploader("CSVファイルをアップロード（例: name, current）", type=["csv"])
if uploaded_csv is not None:
    df = pd.read_csv(uploaded_csv)
else:
    # デモ用のサンプルデータ
    df = pd.DataFrame({
        "name": gdf[ID_COL],
        "current": [int(gdf.iloc[i][CAP_COL] * 0.4 + i * 5) for i in range(len(gdf))]
    })

# マージ（GeoJSON×CSV）
merged = gdf.merge(df, left_on=ID_COL, right_on="name", how="left")
merged["current"] = merged["current"].fillna(0).astype(int)
merged["capacity"] = merged[CAP_COL].astype(int)
merged["percent"] = merged["current"] / merged["capacity"] * 100

# 色分け関数
def get_color(percent):
    if percent < 70:
        return "green"
    elif percent < 90:
        return "yellow"
    elif percent < 100:
        return "red"
    else:
        return "black"

# Foliumマップ作成
center = [merged.geometry.y.mean(), merged.geometry.x.mean()]
m = folium.Map(location=center, zoom_start=13, tiles="cartodbpositron")

for _, row in merged.iterrows():
    percent = row["percent"]
    color = get_color(percent)
    popup_text = f"{row[ID_COL]}<br>収容人数: {row['current']} / {row['capacity']}<br>利用率: {percent:.1f}%"
    CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=max(7, min(30, row["capacity"] / 20)),  # 大きさは適宜調整
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        popup=folium.Popup(popup_text, max_width=300),
    ).add_to(m)

st.markdown("""
#### 地図の使い方
- 円の大きさ＝収容人数
- 色＝収容率（緑：安全／黄：注意／赤：満杯／黒：超過）
- 円をクリックで詳細表示
""")

st_folium(m, width=1000, height=600)

# データテーブルも表示
st.markdown("#### 避難所一覧と利用率")
st.dataframe(merged[[ID_COL, "capacity", "current", "percent"]].rename(columns={
    ID_COL: "避難所名",
    "capacity": "収容人数",
    "current": "現在の人数",
    "percent": "利用率(%)"
}).style.format({"利用率(%)": "{:.1f}"}))
