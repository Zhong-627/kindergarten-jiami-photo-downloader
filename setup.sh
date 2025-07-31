#!/bin/bash

# 加米幼兒園相簿自動下載程式 - 安裝腳本
# 適用於 macOS (MacBook Air M1)

set -e  # 遇到錯誤時立即停止

echo "======================================"
echo "加米幼兒園相簿下載器 - 安裝腳本"
echo "======================================"

# 檢查作業系統
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "錯誤: 此腳本僅適用於 macOS"
    exit 1
fi

# 檢查 Python 版本
echo "檢查 Python 環境..."
if ! command -v python3 &> /dev/null; then
    echo "錯誤: 未找到 Python 3，請先安裝 Python 3.8 或以上版本"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "找到 Python $PYTHON_VERSION"

# 檢查 Python 版本是否符合需求
REQUIRED_VERSION="3.8"
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "錯誤: Python 版本需要 3.8 或以上，目前版本: $PYTHON_VERSION"
    exit 1
fi

# 檢查 pip
echo "檢查 pip..."
if ! command -v pip3 &> /dev/null; then
    echo "錯誤: 未找到 pip3，請先安裝 pip"
    exit 1
fi

# 檢查 Chrome 瀏覽器
echo "檢查 Chrome 瀏覽器..."
if ! ls /Applications/Google\ Chrome.app &> /dev/null; then
    echo "警告: 未找到 Google Chrome，請確保已安裝 Chrome 瀏覽器"
    echo "下載地址: https://www.google.com/chrome/"
    read -p "是否繼續安裝？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 建立虛擬環境（可選）
read -p "是否要建立 Python 虛擬環境？建議選擇 y (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "建立虛擬環境..."
    python3 -m venv venv
    
    echo "啟動虛擬環境..."
    source venv/bin/activate
    
    echo "升級 pip..."
    pip install --upgrade pip
    
    echo ""
    echo "注意: 虛擬環境已建立，每次使用前請執行："
    echo "source venv/bin/activate"
    echo ""
fi

# 安裝相依套件
echo "安裝 Python 相依套件..."
pip3 install -r requirements.txt

# 建立下載目錄
echo "建立下載目錄..."
DOWNLOAD_DIR="/Users/$(whoami)/Desktop/加米相簿"
mkdir -p "$DOWNLOAD_DIR"
mkdir -p "$DOWNLOAD_DIR/校園相簿"
mkdir -p "$DOWNLOAD_DIR/班級相簿"
echo "下載目錄已建立: $DOWNLOAD_DIR"

# 設定執行權限
echo "設定檔案權限..."
chmod +x main.py
chmod +x setup.sh

# 測試安裝
echo "測試安裝..."
python3 -c "
import selenium
import requests
import PIL
import tqdm
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
print('所有套件測試成功!')
"

echo ""
echo "======================================"
echo "安裝完成！"
echo "======================================"
echo ""
echo "使用方式："
echo "1. 下載最近一週的照片："
echo "   python3 main.py"
echo ""
echo "2. 指定日期範圍："
echo "   python3 main.py --start-date 2024-01-01 --end-date 2024-01-31"
echo ""
echo "3. 只下載校園相簿："
echo "   python3 main.py --type school"
echo ""
echo "4. 乾跑模式（不實際下載）："
echo "   python3 main.py --dry-run"
echo ""
echo "5. 查看所有選項："
echo "   python3 main.py --help"
echo ""
echo "下載目錄: $DOWNLOAD_DIR"
echo ""
echo "注意事項："
echo "- 首次執行時會自動下載 Chrome WebDriver"
echo "- 確保網路連線穩定"
echo "- 建議先用 --dry-run 測試"
echo "- 大量下載時請預留足夠硬碟空間"
echo ""
echo "如需設定定期執行，請參考 cron 設定說明"
echo "======================================"