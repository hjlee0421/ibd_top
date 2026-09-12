import time
import random
import pandas as pd
from bs4 import BeautifulSoup

# undetected_chromedriver 대신 순수 Selenium 사용
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

def setup_driver():
    chrome_options = Options()
    
    # 깃허브 액션(리눅스) 필수 설정
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    # 봇 차단 방지를 위한 일반 사용자 위장 (User-Agent 강제 변경)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 자동화 봇(Bot) 속성 숨기기
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # Selenium 4.10 이상부터는 Service와 함께 드라이버 경로를 지정하지 않으면,
    # 내장된 Selenium Manager가 알아서 현재 크롬 버전에 맞는 드라이버를 찾아 다운로드하고 실행합니다. (버전 충돌 원천 차단)
    service = Service() 
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # navigator.webdriver 플래그를 false로 조작하여 봇 탐지 회피
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def update_ibd_top_tickers(excel_path):
    df = pd.read_excel(excel_path)
    tasks = []
    
    for index, row in df.iterrows():
        if "1위_티커" in df.columns and "기존_티커" in df.columns:
            ticker = row['기존_티커'] if pd.isna(row['1위_티커']) or row['1위_티커'] == 'N/A' else row['1위_티커']
        elif "TICKER" in df.columns:
            ticker = row["TICKER"]
        else:
            ticker = row.iloc[0] 
            
        old_rank = "N/A"
        if "INDUSTRY GROUP RANKING" in df.columns:
            old_rank = row["INDUSTRY GROUP RANKING"]
        elif "INDUSTRY GROUP RANK" in df.columns:
            old_rank = row["INDUSTRY GROUP RANK"]
            
        if pd.notna(ticker):
            tasks.append({"ticker": str(ticker).strip(), "old_rank": old_rank})

    results = []
    total_items = len(tasks)

    print(f"🚀 총 {total_items}개 그룹 스크래핑 시작 (순수 Selenium Manager 환경)")

    i = 0
    chunk_count = 1

    while i < total_items:
        current_chunk_size = random.randint(10, 15)
        chunk_end_idx = min(i + current_chunk_size, total_items)
        chunk_tasks = tasks[i:chunk_end_idx]

        print(f"==================================================")
        print(f"🔄 [청크 {chunk_count}] 브라우저 시작 (진행도: {i+1} ~ {chunk_end_idx} / {total_items})")
        print(f"==================================================")

        driver = setup_driver()

        for j, task in enumerate(chunk_tasks):
            ticker = task["ticker"]
            old_rank = task["old_rank"]
            
            url = f"https://research.investors.com/quote.aspx?symbol={ticker}"
            scraped_data = {
                "기존_티커": ticker, "상태": "대기", "기존_그룹_랭킹": old_rank,
                "새_INDUSTRY_GROUP_RANK": "N/A", "순위_변동": "N/A", 
                "SECTOR": "N/A", "INDUSTRY_GROUP": "N/A",
                "1위_티커": "N/A", "1위_주소": "N/A",
            }

            try:
                driver.get(url)
                time.sleep(10)
                soup = BeautifulSoup(driver.page_source, "html.parser")

                comp_content = soup.find("div", class_="companyContent")
                if comp_content:
                    uls = comp_content.find_all("ul")
                    for ul in uls:
                        lis = ul.find_all("li")
                        if len(lis) >= 2:
                            key = lis[0].get_text(strip=True).upper()
                            val = lis[1].get_text(separator=" ", strip=True)
                            if "SECTOR" in key: scraped_data["SECTOR"] = val
                            elif "INDUSTRY GROUP RANK" in key: scraped_data["새_INDUSTRY_GROUP_RANK"] = val
                            elif "INDUSTRY GROUP" in key: scraped_data["INDUSTRY_GROUP"] = val

                if scraped_data["새_INDUSTRY_GROUP_RANK"] != "N/A" and scraped_data["기존_그룹_랭킹"] != "N/A":
                    try:
                        new_r = int(float(scraped_data["새_INDUSTRY_GROUP_RANK"]))
                        old_r = int(float(scraped_data["기존_그룹_랭킹"]))
                        diff = old_r - new_r 
                        if diff > 0: scraped_data["순위_변동"] = f"▲ {diff}"
                        elif diff < 0: scraped_data["순위_변동"] = f"▼ {abs(diff)}"
                        else: scraped_data["순위_변동"] = "-"
                    except:
                        scraped_data["순위_변동"] = "확인불가"

                grp_ldrs = soup.find("div", id="grpLdrs")
                is_current_number_one = False
                if grp_ldrs:
                    rank_span = grp_ldrs.find("span", id="ctl00_ctl00_secondaryContent_leftContent_GrpLeaders_ltlSymbolRank")
                    if rank_span and rank_span.get_text(strip=True) == "1":
                        is_current_number_one = True
                    else:
                        rank_tail = grp_ldrs.find("span", id="ctl00_ctl00_secondaryContent_leftContent_GrpLeaders_lblRankN")
                        if rank_tail and "1st" in rank_tail.get_text(strip=True):
                            is_current_number_one = True

                    if is_current_number_one:
                        scraped_data["1위_티커"] = ticker
                        scraped_data["1위_주소"] = driver.current_url  
                        scraped_data["상태"] = "성공 (현재 티커 1위 유지)"
                    else:
                        first_symbol_div = grp_ldrs.find("div", id="ctl00_ctl00_secondaryContent_leftContent_GrpLeaders_pnlFirstSymbol")
                        if first_symbol_div:
                            a_tag = first_symbol_div.find("a", class_="stockRoll")
                            if a_tag:
                                scraped_data["1위_티커"] = a_tag.get_text(strip=True)
                                href = a_tag.get("href", "")
                                if href.startswith("/"): href = "https://research.investors.com" + href
                                scraped_data["1위_주소"] = href
                                scraped_data["상태"] = f"성공 (새 1위 포착)"
                        else:
                            scraped_data["상태"] = "실패 (1위 티커 찾지 못함)"
            except Exception as e:
                scraped_data["상태"] = f"에러 발생"
                
            results.append(scraped_data)
            print(f"  -> {ticker} 결과: {scraped_data['상태']}")

            if j < len(chunk_tasks) - 1:
                short_sleep = random.uniform(10.0, 20.0)
                time.sleep(short_sleep)

        try: 
            driver.quit()
        except: 
            pass

        if chunk_end_idx < total_items:
            long_sleep = random.randint(300, 600)
            print(f"\n[IP 차단 방어] 브라우저를 닫고 {long_sleep//60}분 {long_sleep%60}초 동안 대기합니다...\n")
            time.sleep(long_sleep)

        i += current_chunk_size
        chunk_count += 1

    df_results = pd.DataFrame(results)
    df_results["새_INDUSTRY_GROUP_RANK_NUM"] = pd.to_numeric(df_results["새_INDUSTRY_GROUP_RANK"], errors="coerce")
    df_results = df_results.sort_values(by="새_INDUSTRY_GROUP_RANK_NUM")

    final_cols = ["새_INDUSTRY_GROUP_RANK", "순위_변동", "기존_그룹_랭킹", "SECTOR", "INDUSTRY_GROUP", "1위_티커", "1위_주소", "기존_티커", "상태"]
    df_final = df_results[final_cols].copy()
    
    df_final.rename(
        columns={
            "새_INDUSTRY_GROUP_RANK": "INDUSTRY GROUP RANKING", 
            "INDUSTRY_GROUP": "INDUSTRY GROUP", 
            "기존_그룹_랭킹": "PREV RANK", 
            "순위_변동": "RANK CHANGE"
        }, 
        inplace=True
    )
    
    df_final.to_excel(excel_path, index=False)
    print("🎉 데이터 업데이트가 완료되었습니다.")

if __name__ == "__main__":
    excel_file_path = "IBD_Updated_Top1_Groups.xlsx" 
    update_ibd_top_tickers(excel_file_path)
