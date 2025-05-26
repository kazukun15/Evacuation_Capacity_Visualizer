import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium import CircleMarker
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(page_title="避難所収容状況マップ", layout="wide")

st.title("避難所収容状況マップ")
st.markdown("""
#### このアプリは避難所の位置・収容状況を地図と表でわかりやすく可視化します。

1. **サイドバー**からGeoJSONとCSVをアップロード
2. **カラムを選択**
3. 地図と表に即反映
""")

with st.sidebar:
    st.header("ファイル選択 & 設定")
    geojson_file = st.file_uploader("GeoJSONファイル（避難所位置）", type=["geojson"])
    csv_file = st.file_uploader("CSVファイル（現在の人数等）", type=["csv"])
    st.markdown("---")
    st.subheader("地図設定")
    default_lat = st.number_input("初期地図の緯度", value=34.25747112128196, format="%.8f")
    default_lon = st.number_input("初期地図の経度", value=133.20433973807084, format="%.8f")
    min_radius = st.slider("円の最小半径", 3, 30, 7)
    max_radius = st.slider("円の最大半径", 10, 80, 30)
    ratio = st.slider("収容人数→半径係数", 5, 100, 20)
    st.markdown("---")
    st.subheader("色分け閾値（混雑率%）")
    threshold1 = st.slider("緑→黄", 10, 99, 70)
    threshold2 = st.slider("黄→赤", threshold1+1, 100, 90)
    threshold3 = st.slider("赤→黒", threshold2+1, 300, 100)
    thresholds = [threshold1, threshold2, threshold3]

def safe_read_geojson(file):
    try:
        gdf = gpd.read_file(file)
        return gdf
    except Exception as e:
        st.error(f"GeoJSON読込エラー: {e}")
        return None

def safe_read_csv(file):
    try:
        df = pd.read_csv(file)
        return df
    except Exception as e:
        st.error(f"CSV読込エラー: {e}")
        return None

gdf = safe_read_geojson(geojson_file) if geojson_file else None
df_csv = safe_read_csv(csv_file) if csv_file else None

if gdf is None:
    from shapely.geometry import Point
    gdf = gpd.GeoDataFrame({
        "避難所名": ["本庁舎", "分庁舎", "小学校", "公民館"],
        "収容人数": [200, 150, 100, 80],
        "geometry": [Point(default_lon, default_lat),
                     Point(default_lon+0.01, default_lat+0.005),
                     Point(default_lon+0.013, default_lat-0.005),
                     Point(default_lon-0.005, default_lat+0.008)]
    }, crs="EPSG:4326")
if df_csv is None:
    df_csv = pd.DataFrame({
        "施設名": ["本庁舎", "分庁舎", "小学校", "公民館"],
        "現在人数": [40, 75, 99, 90]
    })

# --- カラム自動検出＆ユーザー選択 ---
st.markdown("### ① カラム選択")

geo_cols = gdf.columns.tolist()
point_col_candidates = [c for c in geo_cols if c.lower() in ["geometry", "geom"]]
# ★ 選択したカラムを変数として使う
id_col = st.selectbox("GeoJSONの『施設名（避難所名）』カラム", [c for c in geo_cols if c != "geometry"], index=0)
cap_col = st.selectbox("GeoJSONの『最大収容人数』カラム", [c for c in geo_cols if c != "geometry"], index=1 if len(geo_cols)>1 else 0)
geometry_col = st.selectbox("GeoJSONのgeometryカラム", point_col_candidates, index=0)

csv_cols = df_csv.columns.tolist()
csv_id_col = st.selectbox("CSVの『施設名（避難所名）』カラム", csv_cols, index=0)
csv_current_col = st.selectbox("CSVの『現在人数』カラム", csv_cols, index=1 if len(csv_cols)>1 else 0)

# --- データ処理 ---
try:
    merged = gdf.merge(df_csv, left_on=id_col, right_on=csv_id_col, how="left")
    merged["capacity"] = merged[cap_col].fillna(1).astype(int)
    merged["current"] = merged[csv_current_col].fillna(0).astype(int)
    with np.errstate(divide="ignore", invalid="ignore"):
        merged["percent"] = np.where(
            merged["capacity"] > 0,
            merged["current"] / merged["capacity"] * 100,
            np.nan
        )
    if not all(merged[geometry_col].apply(lambda x: x.geom_type == "Point")):
        st.warning("注意: geometryカラムは全てPoint型にしてください。")
except Exception as e:
    st.error(f"データ処理エラー: {e}")
    st.stop()

# --- 色分け関数 ---
def get_color(percent, thresholds):
    if np.isnan(percent):
        return "#A9A9A9"
    if percent < thresholds[0]:
        return "#4CAF50"
    elif percent < thresholds[1]:
        return "#FFD600"
    elif percent < thresholds[2]:
        return "#E53935"
    else:
        return "#222222"

# --- 地図 ---
st.markdown("### ② 地図表示（インタラクティブ）")
m = folium.Map(location=[default_lat, default_lon], zoom_start=13, tiles="cartodbpositron")
for _, row in merged.iterrows():
    percent = row["percent"]
    color = get_color(percent, thresholds)
    # ★ ポップアップや検索等「全て選択カラム名を使用」
    facility_name = str(row[id_col])
    popup_text = (
        f"<b>{facility_name}</b><br>"
        f"収容人数: <b>{row['current']} / {row['capacity']}</b><br>"
        f"利用率: <b>{percent:.1f}%</b>"
    )
    cap_val = row["capacity"] if pd.notnull(row["capacity"]) else 1
    radius = max(min_radius, min(max_radius, cap_val / ratio))
    CircleMarker(
        location=[row[geometry_col].y, row[geometry_col].x],
        radius=radius,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.75,
        popup=folium.Popup(popup_text, max_width=300),
    ).add_to(m)

st_folium(m, width=1100, height=600)

# --- テーブル・検索 ---
st.markdown("### ③ データテーブル & フィルター")
filter_percent = st.slider("利用率がこの値（％）以上の施設のみ表示", 0, 200, 0)
search_keyword = st.text_input("施設名で検索", "")

# ★ 必ず選択カラムでフィルタ・カウント・表示
table_data = merged.copy()
if search_keyword:
    table_data = table_data[table_data[id_col].astype(str).str.contains(search_keyword, case=False, na=False)]
table_data = table_data[table_data["percent"].fillna(0) >= filter_percent]

st.dataframe(
    table_data[[id_col, "capacity", "current", "percent"]]
    .rename(columns={
        id_col: "施設名",
        "capacity": "収容人数",
        "current": "現在の人数",
        "percent": "利用率(%)"
    }).style.format({"利用率(%)": "{:.1f}"})
)

# --- 施設数カウント（必ず選択カラムでユニーク数） ---
facility_count = table_data[id_col].nunique()
st.success(f"現在表示されている施設数：{facility_count} 箇所")

st.info(
    "カラム選択後、全ての表示や集計が“選択カラム”に基づいて自動で反映されます。"
)
