import streamlit as st
import pandas as pd
import geopandas as gpd
import pydeck as pdk

st.set_page_config(page_title="Evacuation Capacity Visualizer", layout="wide")

st.title("Evacuation Capacity Visualizer")
st.write("Upload a CSV or GeoJSON file with evacuation facilities. The size and color of each circle represent its capacity.")

# カラーマップ関数
def get_color(value, vmin, vmax):
    # 青→黄→赤
    if pd.isna(value):
        return [200, 200, 200, 120]
    pct = (value - vmin) / (vmax - vmin) if vmax > vmin else 0.5
    r = int(255 * pct)
    g = int(255 * (1 - abs(pct - 0.5) * 2))
    b = int(255 * (1 - pct))
    return [r, g, b, 180]

uploaded_file = st.file_uploader("CSVまたはGeoJSONファイルをアップロード", type=["csv", "geojson"])

df = None
gdf = None
if uploaded_file:
    filename = uploaded_file.name.lower()
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif filename.endswith(".geojson"):
            gdf = gpd.read_file(uploaded_file)
            # geometryからlat, lon, capacity抽出
            df = pd.DataFrame()
            df["lat"] = gdf.geometry.y
            df["lon"] = gdf.geometry.x
            # capacity/収容人数の列を探す
            for c in ["capacity", "収容人数"]:
                if c in gdf.columns:
                    df["capacity"] = gdf[c]
                    break
            else:
                df["capacity"] = 0
            if "name" in gdf.columns:
                df["name"] = gdf["name"]
            elif "名称" in gdf.columns:
                df["name"] = gdf["名称"]
    except Exception as e:
        st.error(f"ファイルの読み込みに失敗しました: {e}")

if df is not None and not df.empty:
    st.success(f"{len(df)}件の施設を読み込みました。")
    # capacity列自
