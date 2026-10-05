import streamlit as st
import pandas as pd
import requests
import io
import re
from pathlib import Path

st.set_page_config(page_title="IBD 142 Group Rankings", layout="wide")
st.title("📈 IBD 142 Industry Group Rankings")
st.markdown("매일 업데이트되는 IBD 인더스트리 그룹 최신 1위 종목 트래커")

# 💡 '본인아이디'와 '저장소이름'을 깃허브 주소에 맞게 변경하세요.
excel_url = "https://raw.githubusercontent.com/hjlee0421/ibd_top/main/IBD_Updated_Top1_Groups.xlsx"

@st.cache_data(ttl=600)
def load_data():
    response = requests.get(excel_url)
    response.raise_for_status()
    return pd.read_excel(io.BytesIO(response.content))

@st.cache_data(ttl=600)
def load_last_updated():
    try:
        timestamp = Path(__file__).with_name("last_updated.txt").read_text(encoding="utf-8").strip()
        updated_at = pd.to_datetime(timestamp, utc=True, errors="coerce")
        if pd.isna(updated_at):
            return None
        return updated_at.tz_convert("Asia/Seoul").strftime("%Y-%m-%d %H:%M")
    except OSError:
        return None

try:
    df = load_data()
    last_updated = load_last_updated()
    if last_updated:
        st.caption(f"마지막 업데이트: {last_updated} (한국 시간)")
    else:
        st.caption("마지막 업데이트 정보가 아직 없습니다.")
    
    df.columns = [re.sub(r"\s+", " ", str(column)).strip() for column in df.columns]
    df.rename(columns={"INDUSTRY GROUP RANKING": "RANK", "RANK CHANGE": "CHANGE", "PREV RANK": "PREV"}, inplace=True)
    if "1위_주소" in df.columns:
        df.drop(columns=["1위_주소"], inplace=True)
        
    if "RANK" in df.columns: df["RANK"] = pd.to_numeric(df["RANK"], errors="coerce").astype("Int64")
    if "PREV" in df.columns: df["PREV"] = pd.to_numeric(df["PREV"], errors="coerce").astype("Int64")
        
    def color_rank_change(val):
        if pd.isna(val): return ''
        color = '#FF4B4B' if '▲' in str(val) else '#1E90FF' if '▼' in str(val) else 'gray'
        return f'color: {color}; font-weight: bold;'
    
    st.markdown(
        """
        <style>
        .st-key-mobile_layout { display: none; }
        @media (max-width: 640px) {
            .st-key-desktop_layout { display: none; }
            .st-key-mobile_layout { display: block; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="mobile_layout"):
        st.caption(f"총 {len(df)}개 그룹")
        for _, row in df.iterrows():
            rank = "-" if pd.isna(row.get("RANK")) else int(row["RANK"])
            previous_rank = "-" if pd.isna(row.get("PREV")) else int(row["PREV"])
            change = "-" if pd.isna(row.get("CHANGE")) else str(row["CHANGE"])
            ticker = row.get("1위_티커", "-")
            group_name = row.get("INDUSTRY GROUP", "-")
            sector = row.get("SECTOR", "-")

            with st.container(border=True):
                rank_col, change_col = st.columns([1, 2])
                rank_col.markdown(f"### #{rank}")
                change_col.markdown(f"**변동 {change}** · 이전 #{previous_rank}")
                st.markdown(f"**{ticker}** · {group_name}")
                st.caption(sector)

    with st.container(key="desktop_layout"):
        styled_df = df.style.map(color_rank_change, subset=['CHANGE'])
        st.dataframe(styled_df, width="stretch", height=700, hide_index=True)

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
