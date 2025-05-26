import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium import CircleMarker
from streamlit_folium import st_folium
import numpy as np

# ---- 設定項目（ここを編集するだけで全体に反映） ----
GEOJSON_PATH = "hinanjyo1.geojson"     # ← 半角1へ修正（全角の場合は適宜調整）
GEOJSON_ID_COL = "name"
GEOJSON_CAP_COL = "capacity"
CSV_ID_COL = "name"
CSV_CURRENT_COL = "current"

# マーカー半径の初期値
MIN_MARKER_RADIUS = 7
MAX_MARKER_RADIUS = 30
CAPACITY_TO_RADIUS_RATIO = 20

# 地図のデフォルト座標（例：東京駅）
DEFAULT_LAT = 35.681236
DEFAULT_LON = 139.767125

# ----------------------------------------

def load_geojson_data(file_path, id_col, cap_col):
    try:
        gdf = gpd.read_file(file_path)
    except FileNotFoundError:
        st.error(f"エラー: GeoJSONファイル '{file_path}' が見つかりません。")
        return None
    except Exception as e:
        st.error(f"エラー: GeoJSONファイル読み込み時に問題発生: {e}")
        return None

    required_cols = [id_col, cap_col, "geometry"]
    for col in required_cols:
        if col not in gdf.columns:
            st.error(f"エラー: GeoJSONに必須カラム '{col}' が存在しません。")
            return None
    return gdf

def load_csv_or_create_demo_data(uploaded_file, gdf_for_demo, geojson_id_col, geojson_cap_col, csv_id_col, csv_current_col):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            if csv_id_col not in df.columns or csv_current_col not in df.columns:
                st.error(f"エラー: CSVに '{csv_id_col}' と '{csv_current_col}' カラムが必要です。")
                return None
            return df
        except Exception as e:
            st.error(f"エラー: CSV読み込み時に問題発生: {e}")
            return None
    # デモデータ生成
    demo_df = pd.DataFrame({
        csv_id_col: gdf_for_demo[geojson_id_col],
        csv_current_col: [int(gdf_for_demo.iloc[i][geojson_cap_col] * 0.4 + i * 5) for i in range(len(gdf_for_demo))]
    })
    return demo_df

def merge_and_process_data(gdf, df, geojson_id_col, csv_id_col, geojson_cap_col, csv_current_col):
    merged = gdf.merge(df, left_on=geojson_id_col, right_on=csv_id_col, how="left")
    merged[csv_current_col] = merged[csv_current_col].fillna(0).astype(int)
    merged["capacity"] = merged[geojson_cap_col].fillna(0).astype(int)
    # capacityが0やNaNの場合は利用率0またはNaNで安全
    with np.errstate(divide="ignore", invalid="ignore"):
        merged["percent"] = np.where(
            merged["capacity"] > 0,
            merged[csv_current_col] / merged["capacity"] * 100,
            np.nan  # capacity=0はNaN
        )
    return merged

def get_color(percent, thresholds):
    if np.isnan(percent):
        return "gray"
    if percent < thresholds[0]:
        return "green"
    elif percent < thresholds[1]:
        return "yellow"
    elif percent < thresholds[2]:
        return "red"
    else:
        return "black"

def create_folium_map(data, id_col, cap_col, percent_col, current_col, thresholds, min_r, max_r, ratio):
    if not data.empty and data.geometry.is_valid.all():
        center_lat = data.geometry.y.mean()
        center_lon = data.geometry.x.mean()
    else:
        center_lat = DEFAULT_LAT
        center_lon = DEFAULT_LON

    m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="cartodbpositron")

    for _, row in data.iterrows():
        percent = row[percent_col]
        color = get_color(percent, thresholds)
        popup_text = f"{row[id_col]}<br>収容人数: {row[current_col]} / {row['capacity']}<br>利用率: {percent:.1f}%"
        cap_val = row["capacity"] if pd.notnull(row["capacity"]) else 1
        radius = max(min_r, min(max_r, cap_val / ratio))
        CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_text, max_width=300),
        ).add_to(m)
    return m

# ---- Streamlit UI ----

st.set_page_config(page_title="Evacuation Capacity Visualizer", layout="wide")
st.title("Evacuation Capacity Visualizer（避難所収容状況可視化）")

# サイドバー: パラメータ設定
st.sidebar.header("設定")

# 閾値のカスタマイズ
st.sidebar.subheader("色分け閾値（％）")
green_yellow = st.sidebar.slider("緑→黄の境界", 50, 90, 70)
yellow_red = st.sidebar.slider("黄→赤の境界", green_yellow+1, 99, 90)
red_black = st.sidebar.slider("赤→黒の境界", yellow_red+1, 200, 100)
thresholds = [green_yellow, yellow_red, red_black]

st.sidebar.subheader("マーカーサイズ調整")
MIN_MARKER_RADIUS = st.sidebar.slider("最小半径", 3, 20, MIN_MARKER_RADIUS)
MAX_MARKER_RADIUS = st.sidebar.slider("最大半径", 10, 100, MAX_MARKER_RADIUS)
CAPACITY_TO_RADIUS_RATIO = st.sidebar.slider("収容人数→半径の係数（大きいほど小さい円）", 5, 100, CAPACITY_TO_RADIUS_RATIO)

# CSVアップロード
uploaded_csv = st.sidebar.file_uploader("収容人数CSVアップロード（例: name, current）", type=["csv"])

# データ読み込み
gdf = load_geojson_data(GEOJSON_PATH, GEOJSON_ID_COL, GEOJSON_CAP_COL)
if gdf is None:
    st.stop()
df_pop = load_csv_or_create_demo_data(uploaded_csv, gdf, GEOJSON_ID_COL, GEOJSON_CAP_COL, CSV_ID_COL, CSV_CURRENT_COL)
if df_pop is None:
    st.stop()

# データ統合・処理
merged = merge_and_process_data(gdf, df_pop, GEOJSON_ID_COL, CSV_ID_COL, GEOJSON_CAP_COL, CSV_CURRENT_COL)

# 地図生成
folium_map = create_folium_map(
    merged, GEOJSON_ID_COL, GEOJSON_CAP_COL, "percent", CSV_CURRENT_COL,
    thresholds, MIN_MARKER_RADIUS, MAX_MARKER_RADIUS, CAPACITY_TO_RADIUS_RATIO
)

st.markdown("""
#### 地図の使い方
- 円の大きさ＝収容人数
- 色＝収容率（緑：安全／黄：注意／赤：満杯／黒：超過／灰：無効）
- 円をクリックで詳細情報を表示
- サイドバーで色分けやマーカーサイズを調整できます
""")
st_folium(folium_map, width=1000, height=600)

# フィルタリング機能（オプション）
filter_percent = st.slider("利用率で絞り込む（％以上）", 0, 200, 0)
filtered = merged[merged["percent"].fillna(0) >= filter_percent]

st.markdown("#### 避難所一覧と利用率")
st.dataframe(
    filtered[[GEOJSON_ID_COL, "capacity", CSV_CURRENT_COL, "percent"]].rename(columns={
        GEOJSON_ID_COL: "避難所名",
        "capacity": "収容人数",
        CSV_CURRENT_COL: "現在の人数",
        "percent": "利用率(%)"
    }).style.format({"利用率(%)": "{:.1f}"})
)

# 検索機能（避難所名）
search = st.text_input("避難所名で検索", "")
if search:
    search_filtered = filtered[filtered[GEOJSON_ID_COL].str.contains(search, na=False)]
    st.markdown("#### 検索結果")
    st.dataframe(
        search_filtered[[GEOJSON_ID_COL, "capacity", CSV_CURRENT_COL, "percent"]].rename(columns={
            GEOJSON_ID_COL: "避難所名",
            "capacity": "収容人数",
            CSV_CURRENT_COL: "現在の人数",
            "percent": "利用率(%)"
        }).style.format({"利用率(%)": "{:.1f}"})
    )
