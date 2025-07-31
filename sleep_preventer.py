#!/usr/bin/env python3
"""
防止電腦睡眠模組

在程序執行期間防止系統進入睡眠模式，確保長時間下載任務的穩定性。
支援 macOS 系統。
"""

import os
import sys
import signal
import subprocess
import platform
from typing import Optional
from utils import log_message

class SleepPreventer:
    """防止系統睡眠的控制器"""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.platform = platform.system().lower()
        self.is_active = False
    
    def start(self) -> bool:
        """啟動防睡眠模式"""
        if self.is_active:
            log_message("防睡眠模式已經啟動")
            return True
        
        try:
            if self.platform == "darwin":  # macOS
                return self._start_macos()
            else:
                log_message(f"不支援的作業系統: {self.platform}", "WARNING")
                log_message("請手動保持電腦清醒以確保下載順利完成")
                return False
        
        except Exception as e:
            log_message(f"啟動防睡眠模式失敗: {e}", "ERROR")
            return False
    
    def _start_macos(self) -> bool:
        """在 macOS 上啟動防睡眠模式"""
        try:
            # 使用 caffeinate 命令防止系統睡眠
            # -d: 防止顯示器睡眠
            # -i: 防止系統閒置睡眠
            # -s: 防止系統睡眠（當使用電池時）
            cmd = ['caffeinate', '-d', '-i', '-s']
            
            log_message("正在啟動 macOS 防睡眠模式...")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid  # 創建新的進程組
            )
            
            # 檢查進程是否成功啟動
            if self.process.poll() is None:
                self.is_active = True
                log_message("✓ 防睡眠模式已啟動")
                log_message("  系統將保持清醒直到程序結束")
                return True
            else:
                log_message("caffeinate 程序啟動失敗", "ERROR")
                return False
                
        except FileNotFoundError:
            log_message("找不到 caffeinate 命令", "ERROR")
            log_message("請確認您使用的是 macOS 系統")
            return False
        
        except Exception as e:
            log_message(f"啟動 macOS 防睡眠模式失敗: {e}", "ERROR")
            return False
    
    def stop(self) -> bool:
        """停止防睡眠模式"""
        if not self.is_active:
            return True
        
        try:
            if self.process and self.process.poll() is None:
                log_message("正在停止防睡眠模式...")
                
                # 優雅地終止進程
                try:
                    # 首先嘗試終止整個進程組
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                    
                    # 等待進程結束
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # 如果 5 秒後仍未結束，強制終止
                        log_message("正在強制終止防睡眠進程...")
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                        self.process.wait()
                
                except ProcessLookupError:
                    # 進程已經不存在
                    pass
                
                self.process = None
                self.is_active = False
                log_message("✓ 防睡眠模式已停止")
                return True
            
            else:
                self.is_active = False
                log_message("防睡眠進程已經停止")
                return True
                
        except Exception as e:
            log_message(f"停止防睡眠模式失敗: {e}", "ERROR")
            return False
    
    def is_running(self) -> bool:
        """檢查防睡眠模式是否正在運行"""
        if not self.is_active or not self.process:
            return False
        
        return self.process.poll() is None
    
    def __enter__(self):
        """支援 with 語句的進入方法"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支援 with 語句的退出方法"""
        self.stop()
    
    def __del__(self):
        """析構函數，確保資源清理"""
        if self.is_active:
            self.stop()

def test_sleep_preventer():
    """測試防睡眠功能"""
    print("=" * 60)
    print("防睡眠功能測試")
    print("=" * 60)
    
    # 測試基本功能
    preventer = SleepPreventer()
    
    print(f"當前作業系統: {preventer.platform}")
    print(f"初始狀態: {'活躍' if preventer.is_running() else '未活躍'}")
    
    # 測試啟動
    if preventer.start():
        print(f"啟動後狀態: {'活躍' if preventer.is_running() else '未活躍'}")
        
        # 簡短等待
        import time
        print("等待 3 秒測試穩定性...")
        time.sleep(3)
        
        print(f"等待後狀態: {'活躍' if preventer.is_running() else '未活躍'}")
        
        # 測試停止
        if preventer.stop():
            print(f"停止後狀態: {'活躍' if preventer.is_running() else '未活躍'}")
        else:
            print("停止失敗")
    else:
        print("啟動失敗")
    
    # 測試 with 語句
    print("\n測試 with 語句用法:")
    try:
        with SleepPreventer() as sp:
            print(f"with 語句內狀態: {'活躍' if sp.is_running() else '未活躍'}")
            time.sleep(1)
        print("with 語句結束後，防睡眠應該已自動停止")
        
    except Exception as e:
        print(f"with 語句測試失敗: {e}")
    
    print("=" * 60)
    print("測試完成")

if __name__ == "__main__":
    test_sleep_preventer()