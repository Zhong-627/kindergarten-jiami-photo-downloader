# 加米幼兒園相簿自動下載程式

一個高效能自動化工具，用於下載加米幼兒園的校園相簿和班級相簿照片，支援智慧重複檢測和防睡眠保護功能。

## 功能特色

- ✅ 自動登入並下載校園相簿和班級相簿
- ⚡ 智慧重複檢測，避免重複下載相同照片
- 🛡️ 防睡眠保護，確保長時間下載不中斷
- 📁 按日期和活動名稱自動分類儲存
- 🔍 支援日期範圍和關鍵字過濾
- 📊 詳細下載統計和進度顯示
- 🧹 重複檔案清理和管理工具
- 🔧 測試和維護工具

## 系統需求

- macOS（已在 MacBook Air M1 測試）
- Python 3.8 或以上版本
- Google Chrome 瀏覽器
- 穩定的網路連線

## 安裝步驟

### 1. 下載程式碼
```bash
git clone https://github.com/Zhong-627/kindergarten-jiami-photo-downloader.git
cd kindergarten-jiami-photo-downloader
```

### 2. 安裝相依套件
```bash
# 使用安裝腳本（推薦）
./setup.sh

# 或手動安裝
pip3 install -r requirements.txt
```

### 3. 設定帳號密碼
程式會自動使用內建的登入資訊，若需修改請編輯 `config.py` 檔案。

## 基本使用

### 下載照片
```bash
# 下載最近一週的照片
python3 main.py

# 預覽模式（不實際下載）
python3 main.py --dry-run

# 指定日期範圍
python3 main.py --start-date 2024-01-01 --end-date 2024-01-31

# 指定回溯天數
python3 main.py --days-back 30
```

### 選擇相簿類型
```bash
python3 main.py --type school    # 只下載校園相簿
python3 main.py --type class     # 只下載班級相簿
python3 main.py --type both      # 下載兩種相簿（預設）
```

### 進階選項
```bash
python3 main.py --new-only               # 只下載標示為 NEW 的相簿
python3 main.py --key-word 企鵝,生日      # 關鍵字過濾
python3 main.py --no-sleep-prevention    # 停用防睡眠功能
python3 main.py --verbose                # 詳細輸出模式
```

## 重複檔案管理

### 查看重複檔案
```bash
python3 cleanup_duplicates.py --list
```

### 清理重複檔案
```bash
# 預覽清理操作（建議先執行）
python3 cleanup_duplicates.py --dry-run

# 實際清理（會自動備份）
python3 cleanup_duplicates.py --clean
```

### 重建索引
```bash
# 首次使用或維護時執行
python3 rebuild_hash_index.py
```

## 測試功能

```bash
# 測試重複檢測功能
python3 test_duplicate_detection.py

# 綜合功能測試
python3 test_new_optimizations.py
```

## 檔案結構

下載的照片會自動整理到以下結構：

```
/Volumes/T7 Shield/加米相簿/
├── 校園相簿/
│   ├── 113下K0幼幼企鵝班-神秘的海底世界/
│   │   ├── 2025-07-10_001.jpg
│   │   ├── 2025-07-10_002.jpg
│   │   └── ...
│   └── 113下K0幼幼企鵝班-美好的段落成長/
│       ├── 2025-07-02_001.jpg
│       └── ...
├── 班級相簿/
│   └── 113下K0幼幼企鵝班-Little Kids (美語)/
│       ├── 2025-07-18_001.jpg
│       └── ...
└── download_history.json  # 下載歷史記錄
```

## 使用注意事項

- 首次執行會自動下載 Chrome WebDriver
- 建議先使用 `--dry-run` 模式測試
- 確保有足夠的硬碟空間
- 程式會在每張照片下載間暫停 0.5 秒
- 首次使用建議先執行 `python3 rebuild_hash_index.py` 建立索引
- 防睡眠功能會增加電力消耗，建議接上電源
- 重複檔案清理前會自動建立備份

## 定期執行設定

可以使用 cron 設定定期自動下載：

```bash
# 編輯 crontab
crontab -e

# 每週日晚上 10 點執行
0 22 * * 0 cd /path/to/kindergarten-jiami-photo-downloader && /usr/bin/python3 main.py >> download.log 2>&1

# 每日凌晨 2 點執行（停用防睡眠）
0 2 * * * cd /path/to/kindergarten-jiami-photo-downloader && /usr/bin/python3 main.py --no-sleep-prevention >> download.log 2>&1

# 僅校園相簿每日執行
0 6 * * * cd /path/to/kindergarten-jiami-photo-downloader && /usr/bin/python3 main.py --type school >> download.log 2>&1
```

## 故障排除

### 常見問題

**WebDriver 錯誤**
```bash
# 確保已安裝 Chrome 瀏覽器
pip3 install -r requirements.txt
```

**登入失敗**
- 檢查網路連線
- 確認帳號密碼設定正確

**權限錯誤**
- 確保對下載目錄有寫入權限

**模組匯入錯誤**
```bash
pip3 install -r requirements.txt
```

**雜湊值索引錯誤**
```bash
python3 rebuild_hash_index.py
```

**防睡眠啟動失敗**
```bash
# 檢查 caffeinate 命令
which caffeinate

# 如果不可用，停用防睡眠功能
python3 main.py --no-sleep-prevention
```

## 使用範例

### 首次使用
```bash
# 1. 建立雜湊值索引（如果有現有檔案）
python3 rebuild_hash_index.py

# 2. 測試運行
python3 main.py --dry-run

# 3. 開始下載
python3 main.py
```

### 定期維護
```bash
# 每週維護流程
python3 main.py                           # 下載新照片
python3 cleanup_duplicates.py --dry-run   # 預覽重複檔案
python3 cleanup_duplicates.py --clean     # 清理重複檔案
```

### 特定需求
```bash
# 只下載特定關鍵字的相簿
python3 main.py --key-word "生日,畢業" --new-only

# 下載最近一個月的校園相簿
python3 main.py --type school --days-back 30

# 電池模式（停用防睡眠）
python3 main.py --no-sleep-prevention
```

## 維護腳本

可以建立以下維護腳本 `weekly_maintenance.sh`：

```bash
#!/bin/bash
echo "=== 加米相簿每週維護 ==="
echo "1. 下載新照片..."
python3 main.py

echo "2. 檢查重複檔案..."
python3 cleanup_duplicates.py --dry-run

echo "3. 清理重複檔案..."
python3 cleanup_duplicates.py --clean

echo "4. 系統檢查..."
python3 test_new_optimizations.py
echo "=== 維護完成 ==="
```

## 授權

此程式僅供個人使用，請遵守網站使用條款。