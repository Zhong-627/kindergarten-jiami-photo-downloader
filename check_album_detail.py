#!/usr/bin/env python3
"""
檢查相簿詳細頁面的日期資訊
"""

from browser_handler import BrowserHandler
from config import Config
from utils import log_message
import time

def check_album_detail():
    """檢查相簿詳細頁面"""
    browser = None
    try:
        browser = BrowserHandler()
        
        if not browser.init_browser():
            return False
        
        if not browser.login():
            return False
        
        # 前往校園相簿頁面取得第一個相簿連結
        browser.driver.get(Config.SCHOOL_ALBUMS_URL)
        time.sleep(5)
        
        from selenium.webdriver.common.by import By
        album_links = browser.driver.find_elements(By.CSS_SELECTOR, "a.albumbgphoto")
        
        if not album_links:
            log_message("找不到相簿連結", "ERROR")
            return False
        
        # 進入第一個相簿
        first_album_url = album_links[0].get_attribute("href")
        log_message(f"進入相簿: {first_album_url}")
        
        browser.driver.get(first_album_url)
        time.sleep(5)
        
        # 儲存相簿詳細頁面
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        detail_file = f"/tmp/album_detail_{timestamp}.html"
        with open(detail_file, 'w', encoding='utf-8') as f:
            f.write(browser.driver.page_source)
        log_message(f"相簿詳細頁面已儲存至: {detail_file}")
        
        # 嘗試找到日期相關資訊
        page_text = browser.driver.page_source
        
        # 搜尋可能的日期格式
        import re
        date_patterns = [
            r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
            r"\d{1,2}[-/]\d{1,2}[-/]\d{4}",
            r"\d{4}年\d{1,2}月\d{1,2}日",
            r"上傳時間|更新時間|建立時間|發布時間"
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, page_text)
            if matches:
                log_message(f"找到日期格式 '{pattern}': {matches[:5]}")
        
        # 暫停讓使用者查看
        input("請查看瀏覽器頁面尋找日期資訊，然後按 Enter 鍵繼續...")
        
        return True
        
    except Exception as e:
        log_message(f"檢查失敗: {e}", "ERROR")
        return False
    
    finally:
        if browser:
            browser.close()

if __name__ == "__main__":
    check_album_detail()