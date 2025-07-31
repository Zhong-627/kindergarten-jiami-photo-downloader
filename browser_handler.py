import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from config import Config
from utils import log_message, DateUtils

class BrowserHandler:
    """瀏覽器操作處理器"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
    
    def init_browser(self) -> bool:
        """初始化瀏覽器"""
        try:
            log_message("正在初始化瀏覽器...")
            
            # 設定 Chrome 選項
            chrome_options = Options()
            for option in Config.get_chrome_options():
                chrome_options.add_argument(option)
            
            # 設定下載路徑
            prefs = {
                "download.default_directory": Config.BASE_DOWNLOAD_PATH,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # 初始化 WebDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(Config.IMPLICIT_WAIT)
            self.wait = WebDriverWait(self.driver, Config.BROWSER_TIMEOUT)
            
            log_message("瀏覽器初始化成功")
            return True
            
        except Exception as e:
            log_message(f"瀏覽器初始化失敗: {e}", "ERROR")
            return False
    
    def login(self) -> bool:
        """登入網站"""
        try:
            log_message("正在登入網站...")
            
            # 前往登入頁面
            log_message(f"正在前往登入頁面: {Config.LOGIN_URL}")
            self.driver.get(Config.LOGIN_URL)
            
            # 等待頁面完全載入
            log_message("等待頁面載入...")
            time.sleep(2)
            
            # 列印目前頁面標題和URL以便除錯
            current_url = self.driver.current_url
            page_title = self.driver.title
            log_message(f"目前頁面: {current_url}")
            log_message(f"頁面標題: {page_title}")
            
            # 直接使用已知的帳號欄位選擇器（根據log分析結果）
            try:
                log_message("尋找帳號欄位...")
                username_field = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
                )
                log_message("成功找到帳號欄位")
            except TimeoutException:
                log_message("找不到帳號輸入欄位", "ERROR")
                self._save_page_source_for_debug()
                return False
            
            # 直接使用已知的密碼欄位選擇器（根據log分析結果）
            try:
                log_message("尋找密碼欄位...")
                password_field = self.driver.find_element(By.NAME, "password")
                log_message("成功找到密碼欄位")
            except NoSuchElementException:
                log_message("找不到密碼輸入欄位", "ERROR")
                self._save_page_source_for_debug()
                return False
            
            # 輸入帳號密碼
            log_message("正在輸入帳號密碼...")
            username_field.clear()
            username_field.send_keys(Config.USERNAME)
            log_message("帳號輸入完成")
            
            password_field.clear()
            password_field.send_keys(Config.PASSWORD)
            log_message("密碼輸入完成")
            
            # 直接使用已知的登入按鈕選擇器（根據log分析結果）
            try:
                log_message("尋找登入按鈕...")
                login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                log_message("成功找到登入按鈕")
            except NoSuchElementException:
                log_message("找不到登入按鈕", "ERROR")
                self._save_page_source_for_debug()
                return False
            
            # 點擊登入按鈕
            log_message("正在點擊登入按鈕...")
            login_button.click()
            
            # 等待登入完成，檢查是否跳轉到相簿頁面
            log_message("等待登入完成...")
            time.sleep(2)
            
            final_url = self.driver.current_url
            log_message(f"登入後頁面: {final_url}")
            
            if "Activity" in final_url or "activity" in final_url:
                log_message("登入成功")
                return True
            else:
                log_message(f"登入失敗 - 未跳轉到預期頁面，目前頁面: {final_url}", "ERROR")
                self._save_page_source_for_debug()
                return False
                
        except TimeoutException:
            log_message("登入超時 - 頁面載入時間過長", "ERROR")
            self._save_page_source_for_debug()
            return False
        except Exception as e:
            log_message(f"登入失敗: {e}", "ERROR")
            self._save_page_source_for_debug()
            return False
    
    def _save_page_source_for_debug(self):
        """儲存頁面原始碼用於除錯"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"/tmp/debug_page_{timestamp}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            log_message(f"頁面原始碼已儲存至: {debug_file}", "INFO")
        except Exception as e:
            log_message(f"無法儲存除錯檔案: {e}", "WARNING")
    
    def get_albums_list(self, album_type: str) -> List[Dict[str, Any]]:
        """取得相簿列表（支援分頁）"""
        try:
            base_url = Config.SCHOOL_ALBUMS_URL if album_type == "校園相簿" else Config.CLASS_ALBUMS_URL
            log_message(f"正在取得{album_type}列表...")
            
            all_albums = []
            page_number = 1
            max_album_pages = 5  # 相簿列表最大頁數（增加到5頁）
            
            while page_number <= max_album_pages:
                # 構建分頁URL
                if page_number == 1:
                    page_url = base_url
                else:
                    page_url = f"{base_url}?PageIndex={page_number}"
                
                log_message(f"正在處理{album_type}第 {page_number} 頁: {page_url}")
                self.driver.get(page_url)
                time.sleep(1)  # 減少等待時間
                
                # 檢查瀏覽器會話
                try:
                    self.driver.current_url
                except Exception as e:
                    log_message(f"瀏覽器會話無效: {e}", "ERROR")
                    break
                
                # 取得當前頁面的相簿，傳入相簿類型用於生成正確的連結
                page_albums = self._get_albums_from_current_page(album_type)
                
                if not page_albums:
                    log_message(f"{album_type}第 {page_number} 頁沒有相簿，結束分頁處理")
                    break
                
                # 如果相簿數量少於10個，可能已經是最後一頁
                if len(page_albums) < 10:
                    log_message(f"{album_type}第 {page_number} 頁只有 {len(page_albums)} 個相簿，可能是最後一頁")
                    all_albums.extend(page_albums)
                    break
                
                log_message(f"{album_type}第 {page_number} 頁找到 {len(page_albums)} 個相簿")
                all_albums.extend(page_albums)
                
                page_number += 1
            
            log_message(f"成功取得 {len(all_albums)} 個{album_type}")
            return all_albums
            
        except Exception as e:
            log_message(f"取得{album_type}列表失敗: {e}", "ERROR")
            return []
    
    def _get_albums_from_current_page(self, album_type: str = "校園相簿") -> List[Dict[str, Any]]:
        """從當前頁面取得相簿列表（超級簡化版）"""
        albums = []
        
        try:
            # 根據實際網頁結構，相簿資訊在 .brick2 容器中
            log_message("尋找相簿磚塊容器...")
            
            # 等待磚塊容器載入
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.ID, "freebrick2"))
            )
            
            # 取得所有磚塊元素
            album_elements = self.driver.find_elements(By.CSS_SELECTOR, ".brick2")
            log_message(f"找到 {len(album_elements)} 個相簿磚塊")
            
            # 根據相簿類型決定URL模式
            url_pattern = "School-Album-Detail" if album_type == "校園相簿" else "Class-Album-Detail"
            
            # 批量提取所有資訊，避免多次DOM查詢
            for i, element in enumerate(album_elements):
                try:
                    # 一次性提取所有需要的屬性
                    element_html = element.get_attribute("outerHTML")
                    
                    # 簡單的字符串解析，避免複雜的DOM查詢
                    title = ""
                    link = ""
                    is_new = False
                    
                    # 從HTML中提取標題
                    if "相簿名稱:" in element_html:
                        title_start = element_html.find("相簿名稱:") + 5
                        # 尋找結束位置，可能是換行符或HTML標籤
                        possible_ends = []
                        for end_marker in ["\\n", "<", "\n", "相簿說明:"]:
                            pos = element_html.find(end_marker, title_start)
                            if pos != -1:
                                possible_ends.append(pos)
                        
                        if possible_ends:
                            title_end = min(possible_ends)
                            title = element_html[title_start:title_end].strip()
                            # 清理HTML實體和多餘的符號
                            title = title.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                            if title.endswith('"'):
                                title = title[:-1]
                    
                    # 從HTML中提取連結
                    if "albumId=" in element_html:
                        link_start = element_html.find("albumId=")
                        link_end = element_html.find('"', link_start)
                        if link_end > link_start:
                            link_part = element_html[link_start:link_end]
                            # 解碼HTML實體
                            link_part = link_part.replace("&amp;", "&").replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">")
                            # 根據相簿類型生成正確的連結
                            link = f"https://williamkindergarten.topschool.tw/Activity/{url_pattern}?{link_part}"
                    
                    # 檢查是否為新相簿
                    is_new = "topnews" in element_html
                    
                    # 如果沒有找到標題，使用備用方案
                    if not title and link:
                        if "albumId=" in link:
                            try:
                                album_id = link.split("albumId=")[1].split("&")[0]
                                title = f"相簿_{album_id}"
                            except:
                                title = f"未知相簿_{i+1}"
                        else:
                            title = f"未知相簿_{i+1}"
                    
                    if title and link:
                        # 快速提取相簿ID
                        album_id = None
                        if "albumId=" in link:
                            try:
                                album_id = int(link.split("albumId=")[1].split("&")[0])
                            except (ValueError, IndexError):
                                pass
                        
                        # 簡化的日期推斷
                        estimated_date = self._estimate_album_date(len(albums), album_id, is_new)
                        
                        album_info = {
                            "title": title,
                            "date": estimated_date,
                            "link": link,
                            "date_text": title,
                            "album_id": album_id,
                            "page_order": len(albums),
                            "is_new": is_new
                        }
                        albums.append(album_info)
                        
                        # 只記錄NEW相簿，減少日誌
                        if is_new:
                            log_message(f"解析{album_type}: {title[:30]}... [NEW]")
                        
                except Exception as e:
                    log_message(f"解析相簿 {i+1} 失敗: {e}", "WARNING")
                    continue
            
            log_message(f"成功解析 {len(albums)} 個{album_type}")
            
        except Exception as e:
            log_message(f"從當前頁面取得相簿時發生錯誤: {e}", "ERROR")
        
        return albums
    
    def _find_album_title(self, element) -> Optional[Any]:
        """尋找相簿標題元素"""
        try:
            # 如果元素本身是連結，嘗試取得其文字
            if element.tag_name == "a" and element.text.strip():
                return element
            
            # 否則嘗試在子元素中尋找
            selectors = [
                "h3", "h4", "h5", ".title", ".album-title", 
                ".card-title", "a", ".name", "span", "div"
            ]
            
            for selector in selectors:
                try:
                    child = element.find_element(By.CSS_SELECTOR, selector)
                    if child.text.strip():
                        return child
                except NoSuchElementException:
                    continue
            
            # 如果都找不到，返回元素本身（如果有文字的話）
            if element.text.strip():
                return element
                
        except Exception:
            pass
        return None
    
    def _find_album_date(self, element) -> Optional[Any]:
        """尋找相簿日期元素"""
        selectors = [
            ".date", ".time", ".created", ".album-date",
            ".card-text", "small", ".meta"
        ]
        
        for selector in selectors:
            try:
                return element.find_element(By.CSS_SELECTOR, selector)
            except NoSuchElementException:
                continue
        return None
    
    def _find_album_link(self, element) -> Optional[Any]:
        """尋找相簿連結元素"""
        try:
            # 首先檢查元素本身是否為連結
            if element.tag_name == "a" and element.get_attribute("href"):
                return element
            
            # 然後尋找子元素中的連結
            links = element.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href")
                if href and ("Activity" in href or "album" in href):
                    return link
            
            # 如果沒有找到相關連結，返回第一個連結
            if links:
                return links[0]
                
        except NoSuchElementException:
            pass
        return None
    
    def _parse_album_date(self, date_text: str) -> Optional[datetime]:
        """解析相簿日期"""
        if not date_text:
            return datetime.now()  # 如果沒有日期文字，返回當前日期
        
        # 嘗試從文字中提取日期
        date_patterns = [
            r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",  # YYYY-MM-DD 或 YYYY/MM/DD
            r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",  # MM/DD/YYYY 或 DD/MM/YYYY
            r"(\d{4})年(\d{1,2})月(\d{1,2})日",      # 中文日期格式
            r"(\d{1,3})[上下]",                      # 學期格式，如 "113上" 或 "113下"
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if "年" in pattern:  # 中文格式
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        elif len(groups[0]) == 4:  # YYYY 在前
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        else:  # MM/DD/YYYY 格式
                            month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                        
                        return datetime(year, month, day)
                    elif len(groups) == 1 and ("上" in date_text or "下" in date_text):
                        # 處理學期格式，如 "113下"
                        semester_year = int(groups[0]) + 1911  # 民國年轉西元年
                        if "下" in date_text:
                            # 下學期通常是1-7月
                            return datetime(semester_year + 1, 6, 1)  # 使用6月作為代表
                        else:
                            # 上學期通常是8-12月
                            return datetime(semester_year, 10, 1)  # 使用10月作為代表
                            
                except ValueError:
                    continue
        
        # 如果無法解析，返回當前日期
        log_message(f"無法解析日期，使用當前日期: {date_text}", "WARNING")
        return datetime.now()
    
    def get_album_photos(self, album_url: str, history_manager=None, filter_duplicates: bool = True) -> List[str]:
        """取得相簿中的照片連結（支援分頁）並可選擇性過濾重複"""
        try:
            log_message("正在取得相簿照片...")
            
            self.driver.get(album_url)
            time.sleep(2)
            
            all_photo_urls = []
            page_number = 1
            max_pages = 30  # 照片分頁最大頁數
            
            while page_number <= max_pages:
                log_message(f"正在處理第 {page_number} 頁...")
                
                # 取得當前頁面的照片連結
                current_page_photos = self._get_photos_from_current_page()
                
                if not current_page_photos:
                    log_message(f"第 {page_number} 頁沒有找到照片，結束分頁處理")
                    break
                
                log_message(f"第 {page_number} 頁找到 {len(current_page_photos)} 張照片")
                all_photo_urls.extend(current_page_photos)
                
                # 嘗試前往下一頁（僅使用URL參數方式，最安全）
                if not self._go_to_next_page_by_url():
                    log_message("沒有更多頁面，分頁處理完成")
                    break
                
                page_number += 1
            
            # 移除重複的 URL
            all_photo_urls = list(set(all_photo_urls))
            
            # 過濾掉明顯的縮圖或無效連結
            filtered_urls = []
            for url in all_photo_urls:
                if self._is_full_size_photo_url(url):
                    filtered_urls.append(url)
            
            log_message(f"總共處理 {page_number-1} 頁，成功取得 {len(filtered_urls)} 張照片連結")
            
            # 如果啟用重複過濾且提供了歷史管理器，進行批量重複檢測
            if filter_duplicates and history_manager:
                filtered_urls = self._filter_duplicate_photos(filtered_urls, history_manager)
            
            return filtered_urls
            
        except Exception as e:
            log_message(f"取得相簿照片失敗: {e}", "ERROR")
            return []
    
    def _filter_duplicate_photos(self, photo_urls: List[str], history_manager) -> List[str]:
        """批量檢查並過濾重複照片"""
        try:
            log_message("正在進行批量重複檢測...")
            
            filtered_urls = []
            duplicate_count = 0
            duplicate_info = {}
            
            for i, url in enumerate(photo_urls, 1):
                # 檢查 URL 雜湊值重複（主要檢測機制）
                url_hash = history_manager.get_url_hash_from_url(url)
                if url_hash:
                    is_duplicate, existing_files = history_manager.is_hash_downloaded(url_hash)
                    if is_duplicate:
                        duplicate_count += 1
                        duplicate_info[url] = {
                            "hash": url_hash[:8],
                            "existing_file": existing_files[0]['filename'],
                            "existing_path": existing_files[0]['filepath']
                        }
                        continue
                
                # 檢查是否有相同的 URL 已經在下載記錄中（不同檔名）
                url_already_downloaded = False
                for file_key, record in history_manager.history["downloads"].items():
                    if record.get("url") == url:
                        duplicate_count += 1
                        duplicate_info[url] = f"URL已下載: {record.get('filename', 'unknown')}"
                        url_already_downloaded = True
                        break
                
                if url_already_downloaded:
                    continue
                
                # 非重複的照片
                filtered_urls.append(url)
            
            original_count = len(photo_urls)
            filtered_count = len(filtered_urls)
            
            log_message(f"批量重複檢測完成:")
            log_message(f"  原始照片數: {original_count}")
            log_message(f"  過濾後照片數: {filtered_count}")
            log_message(f"  跳過重複照片: {duplicate_count}")
            
            if duplicate_count > 0:
                log_message(f"  預計節省時間: {duplicate_count * 2}-{duplicate_count * 3} 秒")
            
            return filtered_urls
            
        except Exception as e:
            log_message(f"批量重複檢測失敗: {e}", "ERROR")
            # 如果檢測失敗，返回原始清單
            return photo_urls
    
    def _is_valid_photo_url(self, url: str) -> bool:
        """檢查是否為有效的照片 URL"""
        if not url or url.startswith("data:"):
            return False
        
        # 檢查是否包含圖片副檔名
        photo_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
        url_lower = url.lower()
        
        return any(ext in url_lower for ext in photo_extensions)
    
    def _get_original_photo_url(self, url: str) -> str:
        """嘗試取得原圖 URL"""
        # 如果 URL 包含縮圖標識，嘗試移除以取得原圖
        original_url = url
        
        # 針對加米幼兒園網站的縮圖格式：filename-small.jpg -> filename.jpg
        if "-small." in original_url:
            original_url = original_url.replace("-small.", ".")
        
        # 其他常見的縮圖標識
        thumbnail_patterns = [
            r"_thumb\.", r"_medium\.",
            r"_s\.", r"_m\.", r"_l\.",
            r"\?w=\d+", r"\?h=\d+", r"\?size=\d+"
        ]
        
        for pattern in thumbnail_patterns:
            original_url = re.sub(pattern, ".", original_url)
        
        return original_url
    
    def _is_full_size_photo_url(self, url: str) -> bool:
        """檢查是否為全尺寸照片URL（非縮圖）"""
        if not url:
            return False
        
        # 檢查是否為加米幼兒園的照片服務器
        if "isai-prod-v2.s3.hicloud.net.tw" not in url:
            return False
        
        # 如果包含縮圖標識，則不是全尺寸
        thumbnail_indicators = ["-small.", "_thumb.", "_medium.", "_s.", "_m.", "_l."]
        for indicator in thumbnail_indicators:
            if indicator in url:
                return False
        
        # 檢查URL參數
        if any(param in url for param in ["?w=", "?h=", "?size="]):
            return False
        
        return True
    
    def _get_photos_from_current_page(self) -> List[str]:
        """從當前頁面取得照片連結"""
        photo_urls = []
        
        try:
            # 根據實際結構，尋找相簿詳細頁面中的照片連結
            # 照片在 <a class="photo-gallery albumbgphoto" href="原圖URL"> 中
            photo_links = self.driver.find_elements(By.CSS_SELECTOR, "a.photo-gallery.albumbgphoto")
            
            if photo_links:
                log_message(f"找到 {len(photo_links)} 個photo-gallery連結")
                for link in photo_links:
                    href = link.get_attribute("href")
                    if href and self._is_valid_photo_url(href):
                        photo_urls.append(href)
            
            # 如果沒找到photo-gallery連結，嘗試其他選擇器
            if not photo_urls:
                log_message("未找到photo-gallery連結，嘗試其他方法...")
                
                # 嘗試找 albumbgphoto 連結
                album_links = self.driver.find_elements(By.CSS_SELECTOR, "a.albumbgphoto")
                for link in album_links:
                    href = link.get_attribute("href")
                    if href and self._is_valid_photo_url(href):
                        photo_urls.append(href)
                
                # 如果還是沒找到，嘗試直接找圖片元素
                if not photo_urls:
                    log_message("嘗試直接搜尋圖片元素...")
                    img_elements = self.driver.find_elements(By.CSS_SELECTOR, "img")
                    
                    for img in img_elements:
                        # 取得圖片 URL
                        src = img.get_attribute("src")
                        data_src = img.get_attribute("data-src")
                        
                        # 優先使用 data-src，否則使用 src
                        photo_url = data_src if data_src else src
                        
                        if photo_url and self._is_valid_photo_url(photo_url):
                            # 如果是縮圖，嘗試轉換為原圖
                            original_url = self._get_original_photo_url(photo_url)
                            photo_urls.append(original_url)
            
            # 對照片URL進行自然排序，確保與網站顯示順序一致
            photo_urls = self._sort_photo_urls(photo_urls)
            
        except Exception as e:
            log_message(f"從當前頁面取得照片時發生錯誤: {e}", "WARNING")
        
        return photo_urls
    
    def _load_next_page(self) -> bool:
        """載入下一頁或更多照片"""
        try:
            current_url = self.driver.current_url
            
            # 優先使用URL中的pageIndex參數方式（最直接有效）
            if "pageIndex=" in current_url:
                import re
                match = re.search(r'pageIndex=(\d+)', current_url)
                if match:
                    current_page = int(match.group(1))
                    next_page_url = current_url.replace(f"pageIndex={current_page}", f"pageIndex={current_page + 1}")
                    
                    log_message(f"嘗試訪問下一頁URL: pageIndex={current_page + 1}")
                    self.driver.get(next_page_url)
                    time.sleep(2)
                    
                    # 檢查新頁面是否有照片
                    page_photos = self.driver.find_elements(By.CSS_SELECTOR, "a.photo-gallery.albumbgphoto")
                    if page_photos:
                        log_message(f"成功載入第 {current_page + 1} 頁，找到 {len(page_photos)} 張照片")
                        return True
                    else:
                        log_message(f"第 {current_page + 1} 頁沒有照片")
                        # 不返回原頁面，直接結束
                        return False
            
            # 如果URL沒有pageIndex，嘗試其他方法
            log_message("URL中沒有pageIndex參數，嘗試其他分頁方法...")
            
            # 簡化的按鈕搜尋（避免複雜的XPath導致超時）
            simple_selectors = [
                ".pagination a",
                "a[href*='pageIndex']",
                ".load-more",
                ".show-more"
            ]
            
            for selector in simple_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            href = button.get_attribute("href")
                            text = button.text.lower()
                            
                            # 檢查是否是下一頁連結
                            if href and ("pageindex=" in href.lower() or "page=" in href.lower()):
                                log_message(f"找到分頁連結: {href}")
                                button.click()
                                time.sleep(2)
                                return True
                            
                            # 檢查是否是載入更多按鈕
                            if any(keyword in text for keyword in ["more", "更多", "next", "下一"]):
                                log_message(f"找到載入更多按鈕: {text}")
                                button.click()
                                time.sleep(2)
                                return True
                except (NoSuchElementException, Exception):
                    continue
            
            log_message("沒有找到分頁機制")
            return False
            
        except Exception as e:
            log_message(f"載入下一頁時發生錯誤: {e}", "WARNING")
            return False
    
    def _try_simple_next_page(self) -> bool:
        """簡化版下一頁處理"""
        try:
            current_url = self.driver.current_url
            if "pageIndex=" in current_url:
                import re
                match = re.search(r'pageIndex=(\d+)', current_url)
                if match:
                    current_page = int(match.group(1))
                    next_page_url = current_url.replace(f"pageIndex={current_page}", f"pageIndex={current_page + 1}")
                    
                    self.driver.get(next_page_url)
                    time.sleep(1)
                    
                    # 快速檢查是否有照片
                    page_photos = self.driver.find_elements(By.CSS_SELECTOR, "a.photo-gallery.albumbgphoto")
                    return len(page_photos) > 0
            
            return False
        except Exception:
            return False
    
    def _go_to_next_page_by_url(self) -> bool:
        """透過修改URL參數前往下一頁（最安全的方式）"""
        try:
            current_url = self.driver.current_url
            
            if "pageIndex=" in current_url:
                import re
                match = re.search(r'pageIndex=(\d+)', current_url)
                if match:
                    current_page = int(match.group(1))
                    next_page_url = current_url.replace(f"pageIndex={current_page}", f"pageIndex={current_page + 1}")
                    
                    log_message(f"嘗試前往第 {current_page + 1} 頁")
                    self.driver.get(next_page_url)
                    time.sleep(2)
                    
                    # 檢查新頁面是否有照片
                    page_photos = self.driver.find_elements(By.CSS_SELECTOR, "a.photo-gallery.albumbgphoto")
                    if page_photos:
                        log_message(f"成功載入第 {current_page + 1} 頁，找到 {len(page_photos)} 張照片")
                        return True
                    else:
                        log_message(f"第 {current_page + 1} 頁沒有照片")
                        return False
            
            log_message("URL中沒有pageIndex參數，無法進行分頁")
            return False
            
        except Exception as e:
            log_message(f"前往下一頁時發生錯誤: {e}", "WARNING")
            return False
    
    def _check_if_new_album(self, element) -> bool:
        """檢查相簿是否為新相簿（有topnews類別）"""
        try:
            # 尋找 topnews 類別元素
            topnews_elements = element.find_elements(By.CSS_SELECTOR, ".topnews")
            return len(topnews_elements) > 0
        except Exception:
            return False
    
    def _estimate_album_date(self, page_order: int, album_id: Optional[int], is_new: bool = False) -> datetime:
        """根據NEW標示、頁面順序和相簿ID推斷相簿日期"""
        base_date = datetime.now()
        
        # 如果有NEW標示，認為是最近3天內的相簿
        if is_new:
            days_offset = page_order * 0.5  # NEW相簿間隔更短，0.5天
            days_offset = min(days_offset, 3)  # 最多不超過3天前
        else:
            # 沒有NEW標示的相簿，認為是較舊的
            days_offset = 3 + (page_order * 2)  # 從3天前開始，每個相簿相差2天
        
        # 如果有相簿ID，可以進一步調整
        if album_id is not None:
            # 使用ID的相對大小來微調日期
            # 觀察到的ID範圍大約在 1466000-1604000 之間
            # 使用ID的後幾位數字來微調日期
            id_factor = (album_id % 10000) / 10000.0  # 0.0 到 1.0
            if is_new:
                # NEW相簿的ID微調範圍較小
                days_offset = max(0, days_offset - int(id_factor * 2))
            else:
                # 舊相簿的ID微調範圍較大
                days_offset = max(3, days_offset - int(id_factor * 15))
        
        estimated_date = base_date - timedelta(days=days_offset)
        return estimated_date
    
    def _sort_photo_urls(self, photo_urls: List[str]) -> List[str]:
        """對照片URL進行智慧排序，確保與網站顯示順序一致"""
        try:
            import re
            from config import Config
            
            def is_hash_filename(filename: str) -> bool:
                """檢測是否為雜湊檔名（MD5/SHA等）"""
                # 移除副檔名
                name_without_ext = filename.split('.')[0]
                
                # 檢查是否為純十六進制字符且長度合理（MD5=32, SHA1=40等）
                if re.match(r'^[a-f0-9]{16,64}$', name_without_ext, re.IGNORECASE):
                    return True
                
                # 檢查是否包含下劃線分隔的雜湊值（如：image_abc123_def456.jpg）
                parts = name_without_ext.split('_')
                hash_like_parts = [part for part in parts if re.match(r'^[a-f0-9]{8,}$', part, re.IGNORECASE)]
                if len(hash_like_parts) > 0:
                    return True
                
                return False
            
            def has_meaningful_numbers(filename: str) -> bool:
                """檢測檔名是否包含有意義的數字（非雜湊值）"""
                # 移除雜湊部分，只看其他部分是否有數字
                name_without_ext = filename.split('.')[0]
                
                # 如果是純雜湊，沒有有意義數字
                if is_hash_filename(filename):
                    return False
                
                # 檢查是否包含連續的數字（如：img001, photo_123等）
                return bool(re.search(r'\d{2,}', name_without_ext))
            
            def natural_sort_key(url: str) -> tuple:
                """提取URL中的數字進行自然排序"""
                # 從URL中提取檔名部分
                filename = url.split('/')[-1].split('?')[0]
                
                # 使用正則表達式分離數字和文字部分
                parts = re.split(r'(\d+)', filename)
                
                # 將數字部分轉為整數，文字部分保持字串
                return tuple(int(part) if part.isdigit() else part.lower() for part in parts)
            
            # 根據設定選擇排序方式
            sort_order = getattr(Config, 'PHOTO_SORT_ORDER', 'smart')
            reverse_order = getattr(Config, 'PHOTO_SORT_REVERSE', False)
            
            # 智慧排序邏輯
            if sort_order == 'smart':
                # 檢查第一個檔名來判斷整體排序策略
                if photo_urls:
                    sample_filename = photo_urls[0].split('/')[-1].split('?')[0]
                    
                    if is_hash_filename(sample_filename):
                        # 雜湊檔名：保持DOM順序（網站原始順序）
                        sorted_urls = list(reversed(photo_urls)) if reverse_order else photo_urls
                        log_message(f"檢測到雜湊檔名，使用DOM順序: {len(photo_urls)} 張照片")
                    elif has_meaningful_numbers(sample_filename):
                        # 有意義數字：使用自然排序
                        sorted_urls = sorted(photo_urls, key=natural_sort_key, reverse=reverse_order)
                        log_message(f"檢測到數字檔名，使用自然排序: {len(photo_urls)} 張照片")
                    else:
                        # 其他情況：使用字母排序
                        sorted_urls = sorted(photo_urls, reverse=reverse_order)
                        log_message(f"使用字母排序: {len(photo_urls)} 張照片")
                else:
                    sorted_urls = photo_urls
                    
            elif sort_order == 'natural':
                # 自然排序（數字按數值大小排序）
                sorted_urls = sorted(photo_urls, key=natural_sort_key, reverse=reverse_order)
                log_message(f"照片自然排序完成: {len(photo_urls)} 張照片")
                
            elif sort_order == 'alphabetical':
                # 字母排序
                sorted_urls = sorted(photo_urls, reverse=reverse_order)
                log_message(f"照片字母排序完成: {len(photo_urls)} 張照片")
                
            elif sort_order == 'none':
                # 不排序，保持原始順序
                sorted_urls = list(reversed(photo_urls)) if reverse_order else photo_urls
                log_message(f"保持原始順序: {len(photo_urls)} 張照片")
                
            else:
                # 預設使用智慧排序
                return self._sort_photo_urls(photo_urls)  # 遞歸調用智慧排序
            
            return sorted_urls
            
        except Exception as e:
            log_message(f"照片排序失敗，使用原始順序: {e}", "WARNING")
            return photo_urls
    
    def filter_albums_by_date(self, albums: List[Dict[str, Any]], 
                            start_date: datetime, end_date: datetime, new_only: bool = False, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """根據日期範圍篩選相簿"""
        filtered_albums = []
        
        filter_msg = f"日期篩選範圍: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"
        if new_only:
            filter_msg += " (只篩選NEW相簿)"
        if keywords:
            filter_msg += f" (關鍵字: {', '.join(keywords)})"
        log_message(filter_msg)
        
        for album in albums:
            album_date = album.get("date")
            album_title = album.get("title", "")[:30]
            is_new = album.get("is_new", False)
            new_indicator = " [NEW]" if is_new else ""
            
            if album_date:
                # 轉換為只包含年月日的日期進行比較，忽略時分秒
                album_date_only = album_date.date()
                start_date_only = start_date.date()
                end_date_only = end_date.date()
                
                is_in_range = start_date_only <= album_date_only <= end_date_only
                
                # 檢查NEW條件
                new_criteria = True
                if new_only:
                    new_criteria = is_new
                
                # 檢查關鍵字條件
                keyword_criteria = True
                if keywords:
                    # 大小寫不敏感的關鍵字匹配，只要包含任一關鍵字即符合
                    album_title_lower = album.get("title", "").lower()
                    keyword_criteria = any(keyword.lower() in album_title_lower for keyword in keywords)
                
                # 綜合判斷
                meets_criteria = is_in_range and new_criteria and keyword_criteria
                
                # 構建條件訊息
                criteria_parts = [f"日期符合: {is_in_range}"]
                if new_only:
                    criteria_parts.append(f"NEW: {is_new}")
                if keywords:
                    criteria_parts.append(f"關鍵字: {keyword_criteria}")
                criteria_msg = ", ".join(criteria_parts)
                
                log_message(f"相簿: {album_title}{new_indicator} | 日期: {album_date.strftime('%Y-%m-%d')} | {criteria_msg} | 符合: {meets_criteria}")
                if meets_criteria:
                    filtered_albums.append(album)
            else:
                log_message(f"相簿: {album_title}{new_indicator} | 日期: None | 跳過")
        
        log_message(f"篩選後剩餘 {len(filtered_albums)} 個相簿")
        return filtered_albums
    
    def close(self):
        """關閉瀏覽器"""
        if self.driver:
            try:
                self.driver.quit()
                log_message("瀏覽器已關閉")
            except Exception as e:
                log_message(f"關閉瀏覽器時發生錯誤: {e}", "WARNING")