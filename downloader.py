import os
import time
import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from tqdm import tqdm
from PIL import Image
from io import BytesIO
from config import Config
from utils import (
    log_message, 
    DownloadHistoryManager, 
    FolderManager, 
    FileUtils,
    format_file_size,
    format_duration,
    calculate_download_speed
)
from browser_handler import BrowserHandler
from sleep_preventer import SleepPreventer

class PhotoDownloader:
    """照片下載器"""
    
    def __init__(self):
        self.session = None
        self.history_manager = DownloadHistoryManager(Config.DOWNLOAD_HISTORY_FILE)
        self.folder_manager = FolderManager(Config.BASE_DOWNLOAD_PATH)
        self.download_stats = {
            "total_albums": 0,
            "processed_albums": 0,
            "total_photos": 0,
            "downloaded_photos": 0,
            "skipped_photos": 0,
            "failed_photos": 0,
            "total_size": 0,
            "start_time": None,
            "end_time": None
        }
    
    def init_session(self):
        """初始化下載會話"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': Config.USER_AGENT,
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def download_albums(self, albums_data: Dict[str, List[Dict[str, Any]]], 
                       browser: BrowserHandler, dry_run: bool = False) -> bool:
        """下載相簿"""
        try:
            # 記錄開始時間
            self.download_stats["start_time"] = datetime.now()
            
            if not self.session:
                self.init_session()
            
            # 統計總數
            total_albums = sum(len(albums) for albums in albums_data.values())
            self.download_stats["total_albums"] = total_albums
            
            if total_albums == 0:
                log_message("沒有找到符合條件的相簿")
                return True
            
            log_message(f"開始處理 {total_albums} 個相簿...")
            
            if dry_run:
                log_message("=== 乾跑模式 - 僅顯示將要下載的內容 ===")
                return self._dry_run_albums(albums_data, browser)
            
            # 確保目錄存在
            Config.ensure_directories()
            
            # 使用相簿進度條
            current_album_index = 0
            
            # 處理每種類型的相簿
            for album_type, albums in albums_data.items():
                if not albums:
                    continue
                
                log_message(f"正在處理{album_type}...")
                
                for album in albums:
                    current_album_index += 1
                    log_message(f"[{current_album_index}/{total_albums}] 正在處理相簿: {album['title']}")
                    
                    success = self._download_single_album(album, album_type, browser, current_album_index, total_albums)
                    self.download_stats["processed_albums"] += 1
                    
                    if success:
                        log_message(f"✓ [{current_album_index}/{total_albums}] {album['title']} 下載完成")
                    else:
                        log_message(f"✗ [{current_album_index}/{total_albums}] {album['title']} 下載失敗", "WARNING")
                    
                    # 相簿間暫停
                    time.sleep(0.5)
            
            # 記錄結束時間
            self.download_stats["end_time"] = datetime.now()
            
            # 儲存下載歷史
            self.history_manager.save_history()
            
            # 顯示統計資訊
            self._show_download_summary()
            
            return True
            
        except Exception as e:
            # 記錄結束時間（即使失敗）
            self.download_stats["end_time"] = datetime.now()
            log_message(f"下載過程發生錯誤: {e}", "ERROR")
            return False
    
    def _dry_run_albums(self, albums_data: Dict[str, List[Dict[str, Any]]], 
                       browser: BrowserHandler) -> bool:
        """乾跑模式 - 顯示將要下載的內容"""
        total_photos = 0
        
        for album_type, albums in albums_data.items():
            if not albums:
                continue
            
            print(f"\n=== {album_type} ===")
            
            for album in albums:
                print(f"相簿: {album['title']}")
                print(f"日期: {album['date_text']}")
                print(f"連結: {album['link']}")
                
                # 取得照片數量
                photos = browser.get_album_photos(album['link'])
                total_photos += len(photos)
                print(f"照片數量: {len(photos)}")
                
                # 顯示儲存路徑
                if album['date']:
                    folder_path = self.folder_manager.get_folder_path(
                        album_type, album['date'], album['title']
                    )
                    print(f"儲存路徑: {folder_path}")
                
                print("-" * 50)
                
                time.sleep(0.2)  # 避免過於頻繁的請求
        
        print(f"\n總計: {len(albums_data.get('校園相簿', []))} 個校園相簿, "
              f"{len(albums_data.get('班級相簿', []))} 個班級相簿")
        print(f"預估照片總數: {total_photos}")
        
        return True
    
    def _download_single_album(self, album: Dict[str, Any], album_type: str, 
                              browser: BrowserHandler, current_index: int = 0, total_albums: int = 0) -> bool:
        """下載單個相簿"""
        try:
            log_message(f"正在處理相簿: {album['title']}")
            
            # 取得照片列表（包含預先過濾重複）
            photos = browser.get_album_photos(album['link'], self.history_manager, filter_duplicates=True)
            if not photos:
                log_message("相簿中沒有找到照片或所有照片都已存在", "WARNING")
                return True
            
            self.download_stats["total_photos"] += len(photos)
            
            # 建立資料夾
            if not album['date']:
                log_message("無法解析相簿日期，跳過", "WARNING")
                return False
            
            folder_path = self.folder_manager.get_folder_path(
                album_type, album['date'], album['title']
            )
            self.folder_manager.ensure_folder_exists(folder_path)
            
            # 檢查既有檔案的最大編號
            album_date = album['date'].strftime("%Y-%m-%d")
            existing_files = []
            if os.path.exists(folder_path):
                for file in os.listdir(folder_path):
                    if file.startswith(f"{album_date}_") and file.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        try:
                            number = int(file.split('_')[1].split('.')[0])
                            existing_files.append(number)
                        except (IndexError, ValueError):
                            continue
            
            # 新照片從最大編號+1開始
            start_number = max(existing_files, default=0) + 1
            
            # 下載照片
            success_count = 0
            progress_desc = f"[{current_index}/{total_albums}] {album['title'][:20]}..." if total_albums > 0 else f"下載 {album['title'][:20]}..."
            with tqdm(total=len(photos), desc=progress_desc) as pbar:
                for i, photo_url in enumerate(photos):
                    extension = FileUtils.get_file_extension_from_url(photo_url)
                    filename = f"{album_date}_{start_number + i:03d}{extension}"
                    filepath = os.path.join(folder_path, filename)
                    
                    # 簡單檢查檔案是否已存在（檔案系統層級）
                    if os.path.exists(filepath):
                        pbar.set_description(f"跳過已存在: {filename}")
                        self.download_stats["skipped_photos"] += 1
                        pbar.update(1)
                        continue
                    
                    # 最後檢查 URL+檔名組合（防止極端情況）
                    if self.history_manager.is_downloaded(photo_url, filename):
                        pbar.set_description(f"跳過已下載: {filename}")
                        self.download_stats["skipped_photos"] += 1
                        pbar.update(1)
                        continue
                    
                    # 下載照片
                    success = self._download_photo(photo_url, filepath, filename)
                    if success:
                        success_count += 1
                        self.download_stats["downloaded_photos"] += 1
                    else:
                        self.download_stats["failed_photos"] += 1
                    
                    pbar.set_description(f"正在下載: {filename}")
                    pbar.update(1)
                    
                    # 下載間隔
                    time.sleep(Config.DOWNLOAD_DELAY)
            
            log_message(f"相簿下載完成: {success_count}/{len(photos)} 張照片成功")
            return success_count > 0
            
        except Exception as e:
            log_message(f"下載相簿失敗: {e}", "ERROR")
            return False
    
    def _download_photo(self, url: str, filepath: str, filename: str) -> bool:
        """下載單張照片"""
        retries = 0
        
        while retries < Config.MAX_RETRIES:
            try:
                response = self.session.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                # 檢查內容類型
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    log_message(f"URL 不是圖片: {url}", "WARNING")
                    return False
                
                # 檢查檔案大小
                content_length = response.headers.get('content-length')
                if content_length:
                    file_size = int(content_length)
                    if file_size < 1024:  # 小於 1KB 可能是錯誤頁面
                        log_message(f"檔案太小，可能是錯誤: {filename}", "WARNING")
                        return False
                else:
                    file_size = 0
                
                # 下載檔案
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            if not file_size:
                                file_size += len(chunk)
                
                # 驗證下載的圖片
                if self._validate_image(filepath):
                    # 計算檔案雜湊值，再次檢查是否重複
                    file_hash = FileUtils.calculate_file_hash(filepath)
                    if file_hash:
                        is_duplicate, existing_files = self.history_manager.is_hash_downloaded(file_hash)
                        if is_duplicate:
                            # 下載後發現重複，刪除新下載的檔案
                            os.remove(filepath)
                            log_message(f"下載完成後發現重複內容，已刪除: {filename}")
                            log_message(f"  重複檔案: {existing_files[0]['filepath']}")
                            return False
                    
                    # 記錄下載歷史
                    self.history_manager.add_download_record(
                        url, filename, filepath, file_size
                    )
                    self.download_stats["total_size"] += file_size
                    return True
                else:
                    # 刪除無效檔案
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    log_message(f"下載的檔案無效: {filename}", "WARNING")
                    return False
                
            except requests.exceptions.RequestException as e:
                retries += 1
                if retries < Config.MAX_RETRIES:
                    log_message(f"下載失敗，重試 {retries}/{Config.MAX_RETRIES}: {e}", "WARNING")
                    time.sleep(2 ** retries)  # 指數退避
                else:
                    log_message(f"下載失敗，已達最大重試次數: {filename}", "ERROR")
                    return False
            
            except Exception as e:
                log_message(f"下載過程發生未預期錯誤: {e}", "ERROR")
                return False
        
        return False
    
    def _validate_image(self, filepath: str) -> bool:
        """驗證圖片檔案"""
        try:
            with Image.open(filepath) as img:
                img.verify()
            return True
        except Exception:
            return False
    
    def _show_download_summary(self):
        """顯示下載統計摘要"""
        stats = self.download_stats
        
        print("\n" + "="*60)
        print("下載完成統計")
        print("="*60)
        print(f"處理相簿數: {stats['processed_albums']}/{stats['total_albums']}")
        print(f"總照片數: {stats['total_photos']}")
        print(f"成功下載: {stats['downloaded_photos']}")
        print(f"跳過(已存在): {stats['skipped_photos']}")
        print(f"下載失敗: {stats['failed_photos']}")
        print(f"下載總大小: {format_file_size(stats['total_size'])}")
        
        # 時間統計
        if stats['start_time'] and stats['end_time']:
            duration = (stats['end_time'] - stats['start_time']).total_seconds()
            print(f"總處理時間: {format_duration(duration)}")
            
            # 計算平均時間
            if stats['downloaded_photos'] > 0:
                avg_time_per_photo = duration / stats['downloaded_photos']
                print(f"平均每張照片: {format_duration(avg_time_per_photo)}")
            
            # 計算下載速度
            if stats['total_size'] > 0:
                download_speed = calculate_download_speed(stats['total_size'], duration)
                print(f"平均下載速度: {download_speed}")
        
        # 顯示歷史統計（包含重複檔案資訊）
        history_stats = self.history_manager.get_download_stats()
        print(f"歷史累計檔案: {history_stats['total_files']}")
        print(f"歷史累計大小: {history_stats['total_size_mb']} MB")
        print(f"唯一檔案數: {history_stats['unique_hashes']}")
        
        if history_stats['duplicate_files'] > 0:
            print(f"發現重複檔案: {history_stats['duplicate_files']} 個檔案 ({history_stats['duplicate_hashes']} 組重複)")
            
            # 如果有重複檔案，顯示部分重複資訊
            duplicate_report = self.history_manager.get_duplicate_files_report()
            if duplicate_report and len(duplicate_report) <= 5:  # 只顯示前5組重複
                print("重複檔案範例:")
                for i, (file_hash, files) in enumerate(duplicate_report.items()):
                    if i >= 3:  # 最多顯示3組
                        print(f"  ... 還有 {len(duplicate_report) - 3} 組重複檔案")
                        break
                    print(f"  雜湊值 {file_hash[:8]}... ({len(files)} 個檔案):")
                    for file_info in files[:2]:  # 每組最多顯示2個檔案
                        print(f"    - {file_info['filename']}")
                    if len(files) > 2:
                        print(f"    - ... 還有 {len(files) - 2} 個檔案")
        
        print("="*60)
    
    def close(self):
        """清理資源"""
        if self.session:
            self.session.close()

class AlbumDownloadManager:
    """相簿下載管理器"""
    
    def __init__(self, prevent_sleep: bool = True):
        self.browser = BrowserHandler()
        self.downloader = PhotoDownloader()
        self.prevent_sleep = prevent_sleep
        self.sleep_preventer = None
    
    def download_albums_by_date_range(self, start_date: datetime, end_date: datetime,
                                    album_types: List[str] = None, dry_run: bool = False, new_only: bool = False, keywords: List[str] = None) -> bool:
        """根據日期範圍下載相簿"""
        # 啟動防睡眠模式
        if self.prevent_sleep:
            self.sleep_preventer = SleepPreventer()
            if not self.sleep_preventer.start():
                log_message("無法啟動防睡眠模式，程序將繼續執行", "WARNING")
                self.sleep_preventer = None
        
        try:
            if album_types is None:
                album_types = ["校園相簿", "班級相簿"]
            
            # 初始化瀏覽器
            if not self.browser.init_browser():
                return False
            
            # 登入
            if not self.browser.login():
                return False
            
            albums_data = {}
            
            # 取得各類型相簿
            for album_type in album_types:
                log_message(f"正在取得{album_type}...")
                
                albums = self.browser.get_albums_list(album_type)
                filtered_albums = self.browser.filter_albums_by_date(
                    albums, start_date, end_date, new_only, keywords
                )
                
                albums_data[album_type] = filtered_albums
                log_message(f"{album_type}: 找到 {len(filtered_albums)} 個符合條件的相簿")
            
            # 下載相簿
            success = self.downloader.download_albums(albums_data, self.browser, dry_run)
            
            return success
            
        except Exception as e:
            log_message(f"下載管理過程發生錯誤: {e}", "ERROR")
            return False
        
        finally:
            self._cleanup_resources()
    
    def _cleanup_resources(self):
        """清理所有資源"""
        # 停止防睡眠模式
        if self.sleep_preventer:
            self.sleep_preventer.stop()
            self.sleep_preventer = None
        
        # 清理其他資源
        self.browser.close()
        self.downloader.close()
    
    def close(self):
        """清理資源（向後相容性方法）"""
        self._cleanup_resources()