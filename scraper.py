import time
import random
import pandas as pd
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

def setup_driver():
    options = uc.ChromeOptions()
    # 깃허브 액션 리눅스 서버 필수 설정
    options.add_argument('--headless=new')
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    driver = uc.Chrome(options=options)
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
    driver = setup_driver()

    for j, task in enumerate(tasks):
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
        time.sleep(random.uniform(5.0, 10.0))

    try: driver.quit()
    except: pass

    df_results = pd.DataFrame(results)
    df_results["새_INDUSTRY_GROUP_RANK_NUM"] = pd.to_numeric(df_results["새_INDUSTRY_GROUP_RANK"], errors="coerce")
    df_results = df_results.sort_values(by="새_INDUSTRY_GROUP_RANK_NUM")

    final_cols = ["새_INDUSTRY_GROUP_RANK", "순위_변동", "기존_그룹_랭킹", "SECTOR", "INDUSTRY_GROUP", "1위_티커", "1위_주소", "기존_티커", "상태"]
    df_final = df_results[final_cols].copy()
    df_final.rename(columns={"새_INDUSTRY_GROUP_RANK": "INDUSTRY GROUP RANKING", "INDUSTRY_GROUP": "INDUSTRY GROUP", "기존_그룹_랭킹": "PREV RANK", "순위_변동": "RANK CHANGE"}, inplace=True)
    df_final.to_excel(excel_path, index=False)

if __name__ == "__main__":
    # 구글 드라이브 마운트 제거 후 현재 폴더의 엑셀 파일 바로 지정
    excel_file_path = "IBD_Updated_Top1_Groups.xlsx" 
    update_ibd_top_tickers(excel_file_path)
