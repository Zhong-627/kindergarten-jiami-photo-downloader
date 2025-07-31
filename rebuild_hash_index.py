#!/usr/bin/env python3
"""
重建雜湊值索引腳本

用於為現有的 download_history.json 檔案建立雜湊值索引，
以支援新的重複檔案檢測功能。

使用方法:
    python rebuild_hash_index.py
"""

import os
import sys
import json
from config import Config
from utils import DownloadHistoryManager, log_message

def main():
    """重建雜湊值索引"""
    
    print("=" * 60)
    print("重建雜湊值索引工具")
    print("=" * 60)
    
    history_file = Config.DOWNLOAD_HISTORY_FILE
    
    if not os.path.exists(history_file):
        log_message("找不到下載歷史檔案，無需重建索引", "WARNING")
        return
    
    # 備份原始檔案
    backup_file = f"{history_file}.backup"
    if not os.path.exists(backup_file):
        log_message(f"建立備份檔案: {backup_file}")
        import shutil
        shutil.copy2(history_file, backup_file)
    
    log_message("載入下載歷史...")
    
    # 直接載入 JSON 而不使用 DownloadHistoryManager，避免自動建立索引
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        log_message(f"載入下載歷史失敗: {e}", "ERROR")
        return
    
    if "downloads" not in data:
        log_message("下載歷史格式不正確", "ERROR")
        return
    
    downloads = data["downloads"]
    total_files = len(downloads)
    log_message(f"找到 {total_files} 個下載記錄")
    
    if total_files == 0:
        log_message("沒有下載記錄，無需建立索引")
        return
    
    # 統計資訊
    valid_hashes = 0
    missing_hashes = 0
    invalid_files = 0
    
    # 重建雜湊值索引
    log_message("正在重建雜湊值索引...")
    hash_index = {}
    
    for i, (file_key, record) in enumerate(downloads.items(), 1):
        # 顯示進度
        if i % 100 == 0 or i == total_files:
            print(f"\r處理進度: {i}/{total_files} ({i/total_files*100:.1f}%)", end="", flush=True)
        
        file_hash = record.get("file_hash")
        filepath = record.get("filepath", "")
        
        # 檢查檔案是否存在
        if filepath and not os.path.exists(filepath):
            invalid_files += 1
            continue
        
        # 檢查雜湊值
        if not file_hash:
            missing_hashes += 1
            # 如果檔案存在但沒有雜湊值，嘗試重新計算
            if filepath and os.path.exists(filepath):
                from utils import FileUtils
                file_hash = FileUtils.calculate_file_hash(filepath)
                if file_hash:
                    # 更新記錄中的雜湊值
                    record["file_hash"] = file_hash
                    valid_hashes += 1
                else:
                    continue
            else:
                continue
        else:
            valid_hashes += 1
        
        # 建立索引
        if file_hash not in hash_index:
            hash_index[file_hash] = []
        
        hash_index[file_hash].append({
            "file_key": file_key,
            "filepath": record.get("filepath", ""),
            "filename": record.get("filename", ""),
            "url": record.get("url", "")
        })
    
    print()  # 換行
    
    # 更新資料結構
    data["hash_index"] = hash_index
    
    # 儲存更新後的檔案
    log_message("儲存更新後的下載歷史...")
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log_message("雜湊值索引重建完成!")
    except Exception as e:
        log_message(f"儲存檔案失敗: {e}", "ERROR")
        return
    
    # 統計重複檔案
    duplicate_hashes = {h: files for h, files in hash_index.items() if len(files) > 1}
    duplicate_files_count = sum(len(files) - 1 for files in duplicate_hashes.values())
    
    # 顯示統計結果
    print()
    print("=" * 60)
    print("重建結果統計")
    print("=" * 60)
    print(f"總檔案記錄: {total_files}")
    print(f"有效雜湊值: {valid_hashes}")
    print(f"缺少雜湊值: {missing_hashes}")
    print(f"檔案不存在: {invalid_files}")
    print(f"唯一檔案數: {len(hash_index)}")
    print(f"重複檔案數: {duplicate_files_count} 個檔案 ({len(duplicate_hashes)} 組重複)")
    
    if len(duplicate_hashes) > 0:
        print(f"\n發現 {len(duplicate_hashes)} 組重複檔案:")
        
        # 計算可節省的空間
        total_duplicate_size = 0
        for file_hash, files in duplicate_hashes.items():
            if len(files) > 1:
                # 取第一個檔案的大小
                first_file_key = files[0]["file_key"]
                if first_file_key in downloads:
                    file_size = downloads[first_file_key].get("file_size", 0)
                    duplicate_size = file_size * (len(files) - 1)
                    total_duplicate_size += duplicate_size
        
        if total_duplicate_size > 0:
            from utils import format_file_size
            print(f"重複檔案佔用空間: {format_file_size(total_duplicate_size)}")
        
        # 顯示部分重複檔案範例
        print("\n重複檔案範例 (前5組):")
        for i, (file_hash, files) in enumerate(list(duplicate_hashes.items())[:5]):
            print(f"  {i+1}. 雜湊值 {file_hash[:8]}... ({len(files)} 個檔案)")
            for j, file_info in enumerate(files[:3]):  # 每組最多顯示3個
                print(f"     - {file_info['filename']}")
                if j == 2 and len(files) > 3:
                    print(f"     - ... 還有 {len(files) - 3} 個檔案")
                    break
    
    print("=" * 60)
    log_message("重建完成！現在可以使用新的重複檔案檢測功能。")

if __name__ == "__main__":
    main()