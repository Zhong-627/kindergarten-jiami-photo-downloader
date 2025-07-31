#!/bin/bash
# 加米相簿每週維護腳本
# 使用方法：chmod +x weekly_maintenance.sh && ./weekly_maintenance.sh

set -e  # 遇到錯誤立即停止

echo "============================================================"
echo "🚀 加米相簿下載器 v2.0 - 每週維護腳本"
echo "============================================================"
echo "開始時間: $(date)"
echo ""

# 檢查 Python 環境
echo "📋 環境檢查..."
python3 --version || { echo "❌ Python3 未安裝"; exit 1; }
echo "✅ Python 環境正常"
echo ""

# 1. 下載新照片
echo "📥 步驟 1/5: 下載新照片..."
echo "----------------------------------------"
if python3 main.py; then
    echo "✅ 新照片下載完成"
else
    echo "❌ 下載過程遇到問題"
    echo "請檢查網路連線和登入狀態"
fi
echo ""

# 2. 檢查重複檔案
echo "🔍 步驟 2/5: 檢查重複檔案..."
echo "----------------------------------------"
if python3 cleanup_duplicates.py --dry-run > /tmp/duplicate_check.log 2>&1; then
    echo "✅ 重複檔案檢查完成"
    echo "檢查結果："
    tail -5 /tmp/duplicate_check.log
else
    echo "❌ 重複檔案檢查失敗"
fi
echo ""

# 3. 用戶確認是否清理重複檔案
echo "🧹 步驟 3/5: 清理重複檔案..."
echo "----------------------------------------"
read -p "是否要清理重複檔案？這將節省硬碟空間（y/N）: " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if python3 cleanup_duplicates.py --clean; then
        echo "✅ 重複檔案清理完成"
    else
        echo "❌ 重複檔案清理失敗"
    fi
else
    echo "⏭️  跳過重複檔案清理"
fi
echo ""

# 4. 系統健康檢查
echo "🔧 步驟 4/5: 系統健康檢查..."
echo "----------------------------------------"
if python3 test_new_optimizations.py > /tmp/health_check.log 2>&1; then
    echo "✅ 系統健康檢查通過"
    grep "測試通過" /tmp/health_check.log || echo "詳細結果請查看 /tmp/health_check.log"
else
    echo "❌ 系統健康檢查發現問題"
    echo "詳細結果請查看 /tmp/health_check.log"
fi
echo ""

# 5. 生成統計報告
echo "📊 步驟 5/5: 生成統計報告..."
echo "----------------------------------------"
if python3 -c "
from utils import DownloadHistoryManager
from config import Config
import os

hm = DownloadHistoryManager(Config.DOWNLOAD_HISTORY_FILE)
stats = hm.get_download_stats()

print('📈 下載統計報告:')
print(f'  總檔案數: {stats[\"total_files\"]}')
print(f'  唯一檔案數: {stats[\"unique_hashes\"]}')
print(f'  重複檔案數: {stats[\"duplicate_files\"]}')
print(f'  總大小: {stats[\"total_size_mb\"]} MB')

# 計算資料夾大小
folder_path = '/Volumes/T7 Shield/加米相簿'
if os.path.exists(folder_path):
    # 使用 du 命令計算資料夾大小
    import subprocess
    try:
        result = subprocess.run(['du', '-sh', folder_path], capture_output=True, text=True)
        if result.returncode == 0:
            size = result.stdout.split()[0]
            print(f'  實際佔用空間: {size}')
    except:
        pass
"; then
    echo "✅ 統計報告生成完成"
else
    echo "❌ 統計報告生成失敗"
fi
echo ""

# 完成
echo "============================================================"
echo "🎉 維護完成！"
echo "結束時間: $(date)"
echo ""
echo "💡 提示："
echo "  - 可設定 cron job 自動執行此腳本"
echo "  - 建議每週執行一次維護"
echo "  - 如遇問題請執行: python3 test_new_optimizations.py"
echo "============================================================"

# 清理臨時檔案
rm -f /tmp/duplicate_check.log /tmp/health_check.log