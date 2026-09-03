import streamlit as st
import pandas as pd

# 모바일 가독성을 위한 웹페이지 기본 설정
st.set_page_config(page_title="IBD 142 Group Rankings", layout="wide")
st.title("📈 IBD 142 Industry Group Rankings")
st.markdown("매일 업데이트되는 IBD 인더스트리 그룹 최신 1위 종목 트래커")

# 구글 드라이브 엑셀 파일 직접 다운로드 URL 
FILE_ID = "여기에_메모해둔_파일_ID를_붙여넣으세요"
excel_url = f"https://drive.google.com/uc?id={FILE_ID}&export=download"

@st.cache_data(ttl=600) # 10분 단위 데이터 캐싱 (서버 부하 방지)
def load_data():
    return pd.read_excel(excel_url)

try:
    df = load_data()
    
    # 직관적인 순위 변동 파악을 위한 조건부 서식 지정
    def color_rank_change(val):
        if pd.isna(val): return ''
        color = '#FF4B4B' if '▲' in str(val) else '#1E90FF' if '▼' in str(val) else 'gray'
        return f'color: {color}; font-weight: bold;'
    
    styled_df = df.style.map(color_rank_change, subset=['RANK CHANGE'])
    
    # 모바일 화면 너비에 꽉 차도록 렌더링
    st.dataframe(styled_df, use_container_width=True, height=700)

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
