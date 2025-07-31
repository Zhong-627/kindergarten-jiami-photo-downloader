import os
import json
import re
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, unquote
import unicodedata

class DateUtils:
    """日期處理工具類"""
    
    @staticmethod
    def get_date_range(days_back: int = 7) -> Tuple[datetime, datetime]:
        """取得日期範圍"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        return start_date, end_date
    
    @staticmethod
    def parse_date_string(date_str: str) -> Optional[datetime]:
        """解析日期字串"""
        date_formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m/%d/%Y",
            "%d/%m/%Y"
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None
    
    @staticmethod
    def format_date_for_folder(date: datetime) -> str:
        """格式化日期用於資料夾命名"""
        return date.strftime("%Y-%m-%d")

class FileUtils:
    """檔案處理工具類"""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理檔案名稱，移除無效字元但保留中文"""
        # 移除或替換不安全的字元
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 移除連續的空白字元
        filename = re.sub(r'\s+', ' ', filename)
        # 移除開頭和結尾的空白
        filename = filename.strip()
        # 限制檔名長度
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    @staticmethod
    def generate_folder_name(date: datetime, sequence: int, activity_name: str) -> str:
        """產生資料夾名稱"""
        clean_activity_name = FileUtils.sanitize_filename(activity_name)
        return clean_activity_name
    
    @staticmethod
    def get_file_extension_from_url(url: str) -> str:
        """從 URL 取得檔案副檔名"""
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path)
        _, ext = os.path.splitext(path)
        return ext.lower() if ext else '.jpg'
    
    @staticmethod
    def calculate_file_hash(filepath: str) -> str:
        """計算檔案的 MD5 雜湊值"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""

class DownloadHistoryManager:
    """下載歷史管理器"""
    
    def __init__(self, history_file: str):
        self.history_file = history_file
        self.history = self._load_history()
        self._build_hash_index()
    
    def _load_history(self) -> Dict[str, Any]:
        """載入下載歷史"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 確保有必要的結構
                    if "downloads" not in data:
                        data["downloads"] = {}
                    if "hash_index" not in data:
                        data["hash_index"] = {}
                    return data
            except Exception as e:
                print(f"載入下載歷史失敗: {e}")
                return {"downloads": {}, "hash_index": {}}
        return {"downloads": {}, "hash_index": {}}
    
    def _build_hash_index(self):
        """建立雜湊值索引"""
        self.history["hash_index"] = {}
        for file_key, record in self.history["downloads"].items():
            file_hash = record.get("file_hash")
            if file_hash:
                if file_hash not in self.history["hash_index"]:
                    self.history["hash_index"][file_hash] = []
                self.history["hash_index"][file_hash].append({
                    "file_key": file_key,
                    "filepath": record.get("filepath", ""),
                    "filename": record.get("filename", ""),
                    "url": record.get("url", "")
                })
    
    def save_history(self):
        """儲存下載歷史"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"儲存下載歷史失敗: {e}")
    
    def is_downloaded(self, url: str, filename: str) -> bool:
        """檢查檔案是否已下載（基於 URL + 檔名）"""
        file_key = f"{filename}|{url}"
        return file_key in self.history["downloads"]
    
    def is_hash_downloaded(self, file_hash: str) -> Tuple[bool, List[Dict[str, str]]]:
        """檢查檔案雜湊值是否已存在
        
        Returns:
            Tuple[bool, List[Dict]]: (是否重複, 重複檔案清單)
        """
        if not file_hash or file_hash not in self.history["hash_index"]:
            return False, []
        
        duplicate_files = self.history["hash_index"][file_hash]
        # 檢查檔案是否仍然存在
        existing_files = []
        for file_info in duplicate_files:
            if os.path.exists(file_info["filepath"]):
                existing_files.append(file_info)
        
        return len(existing_files) > 0, existing_files
    
    def get_url_hash_from_url(self, url: str) -> str:
        """從 URL 中提取檔案雜湊值（用於快速檢測）"""
        # URL 格式：https://isai-prod-v2.s3.hicloud.net.tw/image_as0_sid1456_uid605772_albumId1602647_f4e54a16ad37443b96df2a124ba1b6c0.jpg
        # 提取最後的雜湊部分
        import re
        match = re.search(r'_([a-f0-9]{32,})\.', url)
        if match:
            return match.group(1)
        return ""
    
    def add_download_record(self, url: str, filename: str, filepath: str, file_size: int):
        """新增下載記錄"""
        file_key = f"{filename}|{url}"
        file_hash = FileUtils.calculate_file_hash(filepath)
        
        # 新增到下載記錄
        self.history["downloads"][file_key] = {
            "url": url,
            "filename": filename,
            "filepath": filepath,
            "file_size": file_size,
            "download_time": datetime.now().isoformat(),
            "file_hash": file_hash
        }
        
        # 更新雜湊值索引
        if file_hash:
            if file_hash not in self.history["hash_index"]:
                self.history["hash_index"][file_hash] = []
            self.history["hash_index"][file_hash].append({
                "file_key": file_key,
                "filepath": filepath,
                "filename": filename,
                "url": url
            })
    
    def get_download_stats(self) -> Dict[str, int]:
        """取得下載統計"""
        total_files = len(self.history["downloads"])
        total_size = sum(record.get("file_size", 0) for record in self.history["downloads"].values())
        
        # 計算重複檔案統計
        duplicate_hashes = {h: files for h, files in self.history["hash_index"].items() if len(files) > 1}
        duplicate_files_count = sum(len(files) - 1 for files in duplicate_hashes.values())  # 重複檔案數（排除第一個）
        
        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "unique_hashes": len(self.history["hash_index"]),
            "duplicate_files": duplicate_files_count,
            "duplicate_hashes": len(duplicate_hashes)
        }
    
    def get_duplicate_files_report(self) -> Dict[str, List[Dict]]:
        """取得重複檔案報告"""
        duplicate_hashes = {}
        for file_hash, files in self.history["hash_index"].items():
            if len(files) > 1:
                # 檢查檔案是否仍存在
                existing_files = []
                for file_info in files:
                    if os.path.exists(file_info["filepath"]):
                        existing_files.append(file_info)
                
                if len(existing_files) > 1:
                    duplicate_hashes[file_hash] = existing_files
        
        return duplicate_hashes

class FolderManager:
    """資料夾管理器"""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.folder_sequences = {}
    
    def get_folder_path(self, album_type: str, date: datetime, activity_name: str) -> str:
        """取得資料夾路徑，使用活動名稱作為資料夾名稱"""
        folder_name = FileUtils.generate_folder_name(date, 0, activity_name)
        return os.path.join(self.base_path, album_type, folder_name)
    
    def ensure_folder_exists(self, folder_path: str):
        """確保資料夾存在"""
        os.makedirs(folder_path, exist_ok=True)

def log_message(message: str, level: str = "INFO"):
    """記錄訊息"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def format_file_size(size_bytes: int) -> str:
    """格式化檔案大小"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f}{size_names[i]}"

def format_duration(duration_seconds: float) -> str:
    """格式化持續時間"""
    if duration_seconds < 60:
        return f"{duration_seconds:.1f}秒"
    elif duration_seconds < 3600:
        minutes = int(duration_seconds // 60)
        seconds = duration_seconds % 60
        return f"{minutes}分{seconds:.1f}秒"
    else:
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        seconds = duration_seconds % 60
        return f"{hours}小時{minutes}分{seconds:.1f}秒"

def calculate_download_speed(total_size: int, duration_seconds: float) -> str:
    """計算下載速度"""
    if duration_seconds <= 0:
        return "N/A"
    
    speed_bytes_per_sec = total_size / duration_seconds
    return f"{format_file_size(int(speed_bytes_per_sec))}/秒"