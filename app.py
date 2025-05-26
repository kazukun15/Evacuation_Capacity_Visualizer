import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="避難所可視化アプリ", layout="wide")

st.title("避難所データ可視化アプリ")

uploaded_file = st.file_uploader("CSVファイルをアップロードしてください（例: name,lat,lon,capacity）", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)

        required_columns = {"name", "lat", "lon", "capacity"}
        if not required_columns.issubset(df.columns):
            st.error(f"CSVに必要なカラムが不足しています。必要なカラム: {required_columns}")
        else:
            # 色決定ロジック
            def get_color(capacity):
                if capacity < 100:
                    return [0, 0, 255]  # 青
                elif capacity < 500:
                    return [255, 255, 0]  # 黄
                else:
                    return [255, 0, 0]  # 赤

            df["color"] = df["capacity"].apply(get_color)
            df["radius"] = df["capacity"] * 0.1  # 半径スケーリング

            # 地図の中心をデータの中心に設定
            mid_lat = df["lat"].mean()
            mid_lon = df["lon"].mean()

            # pydeckレイヤー
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=df,
                get_position="[lon, lat]",
                get_radius="radius",
                get_fill_color="color",
                pickable=True,
                opacity=0.6,
            )

            # ビュー設定
            view_state = pdk.ViewState(
                latitude=mid_lat,
                longitude=mid_lon,
                zoom=12,
                pitch=45
            )

            # 地図描画
            r = pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                tooltip={"text": "{name}\n収容人数: {capacity}人"}
            )

            st.pydeck_chart(r)

            # データテーブルも表示
            st.subheader("アップロードされたデータ")
            st.dataframe(df)

    except Exception as e:
        st.error(f"ファイル処理中にエラーが発生しました: {e}")
else:
    st.info("CSVファイルをアップロードしてください。")
