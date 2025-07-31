#!/usr/bin/env python3
"""
加米幼兒園相簿自動下載程式

功能：
- 自動登入加米幼兒園網站
- 下載校園相簿和班級相簿
- 按日期分類儲存照片
- 避免重複下載
- 支援命令列參數自訂功能

使用方式：
    python main.py                                      # 下載最近一週
    python main.py --start-date 2024-01-01 --end-date 2024-01-31  # 指定日期範圍
    python main.py --type school                        # 只下載校園相簿
    python main.py --type class                         # 只下載班級相簿
    python main.py --new-only --key-word 企鵝,綿羊      # 只下載包含關鍵字的NEW相簿
    python main.py --dry-run                           # 乾跑模式
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from config import Config
from utils import DateUtils, log_message
from downloader import AlbumDownloadManager

def parse_arguments() -> argparse.Namespace:
    """解析命令列參數"""
    parser = argparse.ArgumentParser(
        description="加米幼兒園相簿自動下載程式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  %(prog)s                                      # 下載最近一週
  %(prog)s --start-date 2024-01-01 --end-date 2024-01-31  # 指定日期範圍
  %(prog)s --type school                        # 只下載校園相簿
  %(prog)s --type class                         # 只下載班級相簿
  %(prog)s --new-only --key-word 企鵝,綿羊      # 只下載包含關鍵字的NEW相簿
  %(prog)s --dry-run                           # 乾跑模式，不實際下載
        """
    )
    
    # 日期範圍參數
    parser.add_argument(
        "--start-date",
        type=str,
        help="開始日期 (格式: YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--end-date", 
        type=str,
        help="結束日期 (格式: YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--days-back",
        type=int,
        default=Config.DEFAULT_DAYS_BACK,
        help=f"下載最近幾天的照片 (預設: {Config.DEFAULT_DAYS_BACK} 天)"
    )
    
    # 相簿類型參數
    parser.add_argument(
        "--type",
        choices=["school", "class", "both"],
        default="both",
        help="下載的相簿類型 (預設: both)"
    )
    
    # 其他選項
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="乾跑模式，只顯示會下載的內容，不實際下載"
    )
    
    parser.add_argument(
        "--no-sleep-prevention",
        action="store_true",
        help="停用防睡眠功能（允許電腦進入睡眠模式）"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="顯示詳細日誌"
    )
    
    parser.add_argument(
        "--new-only",
        action="store_true",
        default=True,
        help="只下載標示為NEW的相簿 (預設: True)"
    )
    
    parser.add_argument(
        "--all-albums",
        action="store_true",
        help="下載所有相簿（覆蓋--new-only預設值）"
    )
    
    parser.add_argument(
        "--key-word",
        type=str,
        help="篩選包含指定關鍵字的相簿，多個關鍵字用逗號分隔 (例: 企鵝,綿羊)"
    )
    
    return parser.parse_args()

def validate_date_arguments(args: argparse.Namespace) -> Tuple[datetime, datetime]:
    """驗證和處理日期參數"""
    try:
        if args.start_date and args.end_date:
            # 使用指定的日期範圍
            start_date = DateUtils.parse_date_string(args.start_date)
            end_date = DateUtils.parse_date_string(args.end_date)
            
            if not start_date:
                raise ValueError(f"無效的開始日期格式: {args.start_date}")
            if not end_date:
                raise ValueError(f"無效的結束日期格式: {args.end_date}")
            
            if start_date > end_date:
                raise ValueError("開始日期不能晚於結束日期")
                
        elif args.start_date or args.end_date:
            raise ValueError("start-date 和 end-date 必須同時指定")
        
        else:
            # 使用預設的天數範圍
            start_date, end_date = DateUtils.get_date_range(args.days_back)
        
        return start_date, end_date
        
    except ValueError as e:
        log_message(f"日期參數錯誤: {e}", "ERROR")
        sys.exit(1)

def get_album_types(type_arg: str) -> List[str]:
    """取得要下載的相簿類型"""
    type_mapping = {
        "school": ["校園相簿"],
        "class": ["班級相簿"],
        "both": ["校園相簿", "班級相簿"]
    }
    return type_mapping.get(type_arg, ["校園相簿", "班級相簿"])

def parse_keywords(keyword_arg: Optional[str]) -> List[str]:
    """解析關鍵字參數"""
    if not keyword_arg:
        return []
    
    # 分割逗號並去除空白
    keywords = [keyword.strip() for keyword in keyword_arg.split(',')]
    # 過濾空字串
    keywords = [keyword for keyword in keywords if keyword]
    
    return keywords

def show_startup_info(start_date: datetime, end_date: datetime, 
                     album_types: List[str], dry_run: bool, new_only: bool = False, keywords: List[str] = None):
    """顯示啟動資訊"""
    print("=" * 60)
    print("加米幼兒園相簿自動下載程式")
    print("=" * 60)
    print(f"日期範圍: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    print(f"下載類型: {', '.join(album_types)}")
    
    filter_conditions = []
    if new_only:
        filter_conditions.append("只下載NEW相簿")
    if keywords:
        filter_conditions.append(f"包含關鍵字: {', '.join(keywords)}")
    
    if filter_conditions:
        print(f"篩選條件: {' + '.join(filter_conditions)}")
    else:
        print("篩選條件: 下載所有符合日期的相簿")
    
    print(f"執行模式: {'乾跑模式 (不實際下載)' if dry_run else '正常下載模式'}")
    print(f"儲存路徑: {Config.BASE_DOWNLOAD_PATH}")
    print("=" * 60)

def main():
    """主程式入口"""
    try:
        # 解析命令列參數
        args = parse_arguments()
        
        # 驗證日期參數
        start_date, end_date = validate_date_arguments(args)
        
        # 取得相簿類型
        album_types = get_album_types(args.type)
        
        # 處理 new_only 邏輯：如果指定 --all-albums，則覆蓋預設的 new_only
        new_only = args.new_only and not args.all_albums
        
        # 解析關鍵字
        keywords = parse_keywords(args.key_word)
        
        # 顯示啟動資訊
        show_startup_info(start_date, end_date, album_types, args.dry_run, new_only, keywords)
        
        # 確認是否繼續
        if not args.dry_run:
            confirm = input("\n確定要開始下載嗎？(y/N): ")
            if confirm.lower() not in ['y', 'yes', '是']:
                log_message("取消下載")
                return
        
        print()  # 空行分隔
        
        # 開始下載
        log_message("程式開始執行...")
        
        # 建立下載管理器（預設啟用防睡眠，除非用戶指定停用）
        prevent_sleep = not args.no_sleep_prevention
        manager = AlbumDownloadManager(prevent_sleep=prevent_sleep)
        success = manager.download_albums_by_date_range(
            start_date=start_date,
            end_date=end_date,
            album_types=album_types,
            dry_run=args.dry_run,
            new_only=new_only,
            keywords=keywords
        )
        
        if success:
            log_message("程式執行完成")
            sys.exit(0)
        else:
            log_message("程式執行失敗", "ERROR")
            sys.exit(1)
            
    except KeyboardInterrupt:
        log_message("程式被使用者中斷", "WARNING")
        sys.exit(130)
        
    except Exception as e:
        log_message(f"程式執行過程發生未預期錯誤: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()