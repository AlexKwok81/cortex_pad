"""配置管理模块 - 负责读写 config.json，支持热重载"""
import json
import os
import sys
import asyncio
from pathlib import Path
from typing import Callable, Optional

# 获取配置文件路径（兼容 PyInstaller 打包和开发环境）
def get_base_path() -> Path:
    """获取基础路径（开发环境为项目根目录，打包后为临时解压目录）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的临时目录
        return Path(sys._MEIPASS)
    return Path(__file__).parent

def get_config_path() -> Path:
    """获取配置文件路径（打包后配置放在 exe 同级目录）"""
    if getattr(sys, 'frozen', False):
        # 打包后配置文件放在 exe 同级目录
        return Path(sys.executable).parent / "config.json"
    return Path(__file__).parent / "config.json"

def get_static_path() -> Path:
    """获取静态文件路径"""
    return get_base_path() / "static"


class ConfigManager:
    """配置管理器 - 读写配置并支持热重载"""

    def __init__(self):
        self._config: dict = {}
        self._config_path = get_config_path()
        self._callbacks: list[Callable] = []
        self._observer = None
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self._config_path, 'r', encoding='utf-8-sig') as f:
                self._config = json.load(f)
        except FileNotFoundError:
            # 首次运行时创建默认配置
            self._config = {"buttons": []}
            self._save_config()
        except json.JSONDecodeError as e:
            print(f"[CONFIG] JSON parse error: {e}")
            self._config = {"buttons": []}

    def _save_config(self):
        """保存配置到文件"""
        with open(self._config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def get_config(self) -> dict:
        """获取当前配置"""
        return self._config.copy()

    def get_buttons(self) -> list:
        """获取按钮列表"""
        return self._config.get("buttons", [])

    def save_config(self, new_config: dict):
        """保存新配置并通知所有监听者"""
        self._config = new_config
        self._save_config()
        # 异步通知所有监听者（配置热重载）
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback())
                else:
                    callback()
            except Exception as e:
                print(f"[CONFIG] Notify listener failed: {e}")

    def on_config_change(self, callback: Callable):
        """注册配置变更监听者"""
        self._callbacks.append(callback)

    def start_watching(self):
        """启动文件监听（可选，用于外部编辑 config.json 时自动重载）"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class ConfigHandler(FileSystemEventHandler):
                def __init__(self, manager: 'ConfigManager'):
                    self.manager = manager
                    self._last_modified = 0

                def on_modified(self, event):
                    if event.src_path == str(self.manager._config_path):
                        # 防抖：避免短时间内多次触发
                        import time
                        now = time.time()
                        if now - self._last_modified > 1:
                            self._last_modified = now
                            print("[CONFIG] Config file changed, reloading...")
                            self.manager._load_config()
                            for cb in self.manager._callbacks:
                                try:
                                    if asyncio.iscoroutinefunction(cb):
                                        asyncio.create_task(cb())
                                    else:
                                        cb()
                                except Exception as e:
                                    print(f"[CONFIG] Notify failed: {e}")

            self._observer = Observer()
            handler = ConfigHandler(self)
            # 监听配置文件所在目录
            watch_dir = str(self._config_path.parent)
            self._observer.schedule(handler, watch_dir, recursive=False)
            self._observer.start()
            print(f"[CONFIG] File watcher started")
        except ImportError:
            print("[CONFIG] watchdog not installed, skipping file watch")


# 全局单例
_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器单例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
