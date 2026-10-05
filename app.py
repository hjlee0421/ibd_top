import streamlit as st
import pandas as pd
import requests
import io
import re
from html import escape
from pathlib import Path
from urllib.parse import urlparse

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
    stock_urls = df["1위_주소"].copy() if "1위_주소" in df.columns else pd.Series("", index=df.index)
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
        .st-key-mobile_layout [data-testid="stElementContainer"]:has(.stock-card) {
            margin-bottom: 0.65rem;
            border: 1px solid rgba(128, 128, 128, 0.35);
            border-radius: 6px;
            overflow: hidden;
        }
        .stock-card {
            display: block;
            box-sizing: border-box;
            padding: 0.75rem;
            color: inherit !important;
            text-decoration: none !important;
        }
        .stock-card:active { background: rgba(128, 128, 128, 0.12); }
        .stock-card:focus-visible {
            outline: 3px solid #1e90ff;
            outline-offset: -3px;
        }
        .stock-card-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 0.75rem;
        }
        .stock-card-rank { font-size: 1.2rem; font-weight: 700; }
        .stock-card-change { text-align: right; }
        .stock-card-main { margin-top: 0.45rem; }
        .stock-card-ticker { font-weight: 700; }
        .stock-card-sector { margin-top: 0.3rem; opacity: 0.72; font-size: 0.9rem; }
        @media (max-width: 640px) {
            .st-key-desktop_layout { display: none; }
            .st-key-mobile_layout { display: block; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="mobile_layout"):
        mobile_rows = df[df["1위_티커"].notna() & df["1위_티커"].astype(str).str.strip().ne("")]
        st.caption(f"총 {len(mobile_rows)}개 그룹")
        for _, row in mobile_rows.iterrows():
            rank = "-" if pd.isna(row.get("RANK")) else int(row["RANK"])
            previous_rank = "-" if pd.isna(row.get("PREV")) else int(row["PREV"])
            change = "-" if pd.isna(row.get("CHANGE")) else str(row["CHANGE"])
            ticker = row.get("1위_티커", "-")
            group_name = row.get("INDUSTRY GROUP", "-")
            sector = row.get("SECTOR", "-")
            stock_url = str(stock_urls.get(row.name, "")).strip()
            parsed_url = urlparse(stock_url)
            safe_url = stock_url if parsed_url.scheme in ("http", "https") and parsed_url.netloc else ""

            card_content = (
                f'<div class="stock-card-header">'
                f'<span class="stock-card-rank">#{escape(str(rank))}</span>'
                f'<span class="stock-card-change">변동 {escape(change)} · 이전 #{escape(str(previous_rank))}</span>'
                f'</div>'
                f'<div class="stock-card-main"><span class="stock-card-ticker">{escape(str(ticker))}</span>'
                f' · {escape(str(group_name))}</div>'
                f'<div class="stock-card-sector">{escape(str(sector))}</div>'
            )
            if safe_url:
                link_label = escape(f"{ticker} {group_name} 종목 정보", quote=True)
                card_html = (
                    f'<a class="stock-card" href="{escape(safe_url, quote=True)}" '
                    f'target="_blank" rel="noopener noreferrer" aria-label="{link_label}">'
                    f'{card_content}</a>'
                )
            else:
                card_html = f'<div class="stock-card">{card_content}</div>'
            st.markdown(card_html, unsafe_allow_html=True)

    with st.container(key="desktop_layout"):
        styled_df = df.style.map(color_rank_change, subset=['CHANGE'])
        st.dataframe(styled_df, width="stretch", height=700, hide_index=True)

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
