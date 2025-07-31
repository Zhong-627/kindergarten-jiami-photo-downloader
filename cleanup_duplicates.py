#!/usr/bin/env python3
"""
重複檔案清理工具

用於清理已下載的重複照片檔案，可以節省硬碟空間。

使用方法:
    python cleanup_duplicates.py --list     # 列出所有重複檔案
    python cleanup_duplicates.py --dry-run  # 顯示會清理哪些檔案（不實際刪除）
    python cleanup_duplicates.py --clean    # 實際清理重複檔案
"""

import os
import sys
import argparse
import shutil
from datetime import datetime
from config import Config
from utils import DownloadHistoryManager, log_message, format_file_size

def list_duplicates(history_manager):
    """列出所有重複檔案"""
    
    print("=" * 80)
    print("重複檔案列表")
    print("=" * 80)
    
    duplicate_report = history_manager.get_duplicate_files_report()
    
    if not duplicate_report:
        log_message("沒有發現重複檔案")
        return
    
    total_duplicates = 0
    total_duplicate_size = 0
    
    for i, (file_hash, files) in enumerate(duplicate_report.items(), 1):
        print(f"\n{i}. 雜湊值: {file_hash}")
        print(f"   重複檔案數量: {len(files)}")
        
        # 計算檔案大小
        file_sizes = []
        for file_info in files:
            file_key = file_info["file_key"]
            record = history_manager.history["downloads"].get(file_key, {})
            file_size = record.get("file_size", 0)
            file_sizes.append(file_size)
            
            filepath = file_info["filepath"]
            exists = "✓" if os.path.exists(filepath) else "✗"
            print(f"   {exists} {file_info['filename']} ({format_file_size(file_size)})")
            print(f"      {filepath}")
        
        # 統計重複檔案（排除第一個）
        if len(files) > 1:
            duplicate_count = len(files) - 1
            duplicate_size = sum(file_sizes[1:])  # 排除第一個檔案
            total_duplicates += duplicate_count
            total_duplicate_size += duplicate_size
    
    print(f"\n" + "=" * 80)
    print(f"統計:")
    print(f"重複檔案組數: {len(duplicate_report)}")
    print(f"可清理的重複檔案數: {total_duplicates}")
    print(f"可節省的空間: {format_file_size(total_duplicate_size)}")
    print("=" * 80)

def dry_run_cleanup(history_manager):
    """乾跑模式 - 顯示會清理哪些檔案"""
    
    print("=" * 80)
    print("乾跑模式 - 重複檔案清理預覽")
    print("=" * 80)
    
    duplicate_report = history_manager.get_duplicate_files_report()
    
    if not duplicate_report:
        log_message("沒有發現重複檔案")
        return 0, 0
    
    files_to_delete = []
    total_size_to_save = 0
    
    for file_hash, files in duplicate_report.items():
        if len(files) > 1:
            # 保留第一個檔案，刪除其他的
            files_to_keep = files[:1]
            files_to_delete_group = files[1:]
            
            print(f"\n雜湊值: {file_hash[:8]}...")
            print(f"保留檔案: {files_to_keep[0]['filename']}")
            print(f"要刪除的檔案:")
            
            for file_info in files_to_delete_group:
                if os.path.exists(file_info["filepath"]):
                    file_key = file_info["file_key"]
                    record = history_manager.history["downloads"].get(file_key, {})
                    file_size = record.get("file_size", 0)
                    
                    files_to_delete.append({
                        "file_info": file_info,
                        "size": file_size
                    })
                    total_size_to_save += file_size
                    
                    print(f"  - {file_info['filename']} ({format_file_size(file_size)})")
                    print(f"    {file_info['filepath']}")
                else:
                    print(f"  - {file_info['filename']} (檔案不存在，將從記錄中移除)")
    
    print(f"\n" + "=" * 80)
    print(f"清理預覽統計:")
    print(f"要刪除的檔案數: {len(files_to_delete)}")
    print(f"可節省的空間: {format_file_size(total_size_to_save)}")
    print("=" * 80)
    
    return len(files_to_delete), total_size_to_save

def cleanup_duplicates(history_manager):
    """實際清理重複檔案"""
    
    print("=" * 80)
    print("重複檔案清理")
    print("=" * 80)
    
    # 先做乾跑檢查
    files_to_delete_count, total_size_to_save = dry_run_cleanup(history_manager)
    
    if files_to_delete_count == 0:
        return
    
    # 確認是否要繼續
    print(f"\n即將刪除 {files_to_delete_count} 個重複檔案，節省 {format_file_size(total_size_to_save)} 空間。")
    response = input("是否要繼續？ (y/N): ").lower().strip()
    
    if response != 'y' and response != 'yes':
        log_message("用戶取消清理操作")
        return
    
    # 建立備份
    backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"/tmp/duplicate_cleanup_backup_{backup_time}"
    os.makedirs(backup_dir, exist_ok=True)
    log_message(f"建立備份目錄: {backup_dir}")
    
    # 開始清理
    duplicate_report = history_manager.get_duplicate_files_report()
    deleted_count = 0
    deleted_size = 0
    removed_records = []
    
    for file_hash, files in duplicate_report.items():
        if len(files) > 1:
            # 保留第一個檔案，刪除其他的
            files_to_delete = files[1:]
            
            for file_info in files_to_delete:
                filepath = file_info["filepath"]
                
                if os.path.exists(filepath):
                    try:
                        # 備份檔案
                        backup_filename = f"{file_info['filename']}_{file_hash[:8]}"
                        backup_path = os.path.join(backup_dir, backup_filename)
                        shutil.copy2(filepath, backup_path)
                        
                        # 刪除檔案
                        file_key = file_info["file_key"]
                        record = history_manager.history["downloads"].get(file_key, {})
                        file_size = record.get("file_size", 0)
                        
                        os.remove(filepath)
                        deleted_count += 1
                        deleted_size += file_size
                        
                        # 標記要從記錄中移除
                        removed_records.append(file_key)
                        
                        log_message(f"已刪除: {file_info['filename']} ({format_file_size(file_size)})")
                        
                    except Exception as e:
                        log_message(f"刪除檔案失敗 {filepath}: {e}", "ERROR")
                
                else:
                    # 檔案不存在，直接從記錄中移除
                    removed_records.append(file_info["file_key"])
                    log_message(f"檔案不存在，從記錄移除: {file_info['filename']}")
    
    # 更新下載歷史記錄
    if removed_records:
        log_message(f"從歷史記錄中移除 {len(removed_records)} 個條目...")
        
        for file_key in removed_records:
            if file_key in history_manager.history["downloads"]:
                del history_manager.history["downloads"][file_key]
        
        # 重建雜湊值索引
        log_message("重建雜湊值索引...")
        history_manager._build_hash_index()
        
        # 儲存更新後的歷史記錄
        history_manager.save_history()
    
    print(f"\n" + "=" * 80)
    print("清理完成統計:")
    print(f"已刪除檔案數: {deleted_count}")
    print(f"節省的空間: {format_file_size(deleted_size)}")
    print(f"備份位置: {backup_dir}")
    print(f"移除的記錄數: {len(removed_records)}")
    print("=" * 80)
    
    log_message("重複檔案清理完成!")

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="重複檔案清理工具")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="列出所有重複檔案")
    group.add_argument("--dry-run", action="store_true", help="顯示會清理哪些檔案（不實際刪除）")
    group.add_argument("--clean", action="store_true", help="實際清理重複檔案")
    
    args = parser.parse_args()
    
    # 檢查下載歷史檔案
    if not os.path.exists(Config.DOWNLOAD_HISTORY_FILE):
        print(f"錯誤: 找不到下載歷史檔案 {Config.DOWNLOAD_HISTORY_FILE}")
        sys.exit(1)
    
    # 初始化歷史管理器
    history_manager = DownloadHistoryManager(Config.DOWNLOAD_HISTORY_FILE)
    
    # 檢查是否有雜湊值索引
    if not history_manager.history.get("hash_index"):
        print("錯誤: 沒有找到雜湊值索引，請先執行 rebuild_hash_index.py")
        sys.exit(1)
    
    if args.list:
        list_duplicates(history_manager)
    elif args.dry_run:
        dry_run_cleanup(history_manager)
    elif args.clean:
        cleanup_duplicates(history_manager)

if __name__ == "__main__":
    main()