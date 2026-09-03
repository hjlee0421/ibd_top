import streamlit as st
import pandas as pd
import requests
import io

st.set_page_config(page_title="IBD 142 Group Rankings", layout="wide")
st.title("📈 IBD 142 Industry Group Rankings")
st.markdown("매일 업데이트되는 IBD 인더스트리 그룹 최신 1위 종목 트래커")

FILE_ID = "1YF3-C7EctvlE4kAUtaOJxKt0lMZ_rBzE"
excel_url = f"https://drive.google.com/uc?id={FILE_ID}&export=download"

@st.cache_data(ttl=600)
def load_data():
    response = requests.get(excel_url)
    response.raise_for_status()
    return pd.read_excel(io.BytesIO(response.content))

try:
    df = load_data()
    
    # 1. 컬럼명 간소화 변경
    df.rename(
        columns={
            "INDUSTRY GROUP RANKING": "RANK",
            "RANK CHANGE": "CHANGE",
            "PREV RANK": "PREV"
        },
        inplace=True
    )
    
    # 2. 웹페이지에서 불필요한 '1위_주소' 컬럼 삭제
    if "1위_주소" in df.columns:
        df.drop(columns=["1위_주소"], inplace=True)
        
    # 3. 랭킹 숫자 소수점 제거 및 정수형 변환
    if "RANK" in df.columns:
        df["RANK"] = pd.to_numeric(df["RANK"], errors="coerce").astype("Int64")
    if "PREV" in df.columns:
        df["PREV"] = pd.to_numeric(df["PREV"], errors="coerce").astype("Int64")
        
    # 4. 조건부 서식 적용 
    def color_rank_change(val):
        if pd.isna(val): return ''
        color = '#FF4B4B' if '▲' in str(val) else '#1E90FF' if '▼' in str(val) else 'gray'
        return f'color: {color}; font-weight: bold;'
    
    styled_df = df.style.map(color_rank_change, subset=['CHANGE'])
    
    # 💡 5. hide_index=True 옵션으로 좌측 숫자 인덱스 숨김 처리
    st.dataframe(
        styled_df, 
        use_container_width=True, 
        height=700, 
        hide_index=True
    )

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
