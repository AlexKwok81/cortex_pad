"""Configuration manager for CortexPad."""
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Callable, Optional


def get_base_path() -> Path:
    """Return the bundled resource directory in PyInstaller builds."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def get_config_path() -> Path:
    """Return the writable runtime config path."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "configs" / "config.json"
    return Path(__file__).parent / "configs" / "config.json"


def get_static_path() -> Path:
    return get_base_path() / "static"


class ConfigManager:
    """Read and write config.json, with optional hot reload callbacks."""

    def __init__(self):
        self._config: dict = {}
        self._config_path = get_config_path()
        self._callbacks: list[Callable] = []
        self._observer = None
        self._load_config()

    def _load_config(self):
        try:
            with open(self._config_path, "r", encoding="utf-8-sig") as f:
                self._config = json.load(f)
        except FileNotFoundError:
            self._config = {"layout": []}
            self._save_config()
        except json.JSONDecodeError as e:
            print(f"[CONFIG] JSON parse error: {e}")
            self._backup_bad_config()
            self._config = {"layout": []}
            self._save_config()

    def _save_config(self):
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._config_path.with_suffix(self._config_path.suffix + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self._config_path)

    def _backup_bad_config(self):
        if not self._config_path.exists():
            return
        try:
            backup_path = self._config_path.with_suffix(self._config_path.suffix + ".bad")
            shutil.copy2(self._config_path, backup_path)
            print(f"[CONFIG] Bad config backed up to {backup_path}")
        except Exception as e:
            print(f"[CONFIG] Failed to back up bad config: {e}")

    def get_config(self) -> dict:
        return self._config.copy()

    def get_buttons(self) -> list:
        return self._config.get("buttons", [])

    def save_config(self, new_config: dict):
        self._config = new_config
        self._save_config()
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback())
                else:
                    callback()
            except Exception as e:
                print(f"[CONFIG] Notify listener failed: {e}")

    def on_config_change(self, callback: Callable):
        self._callbacks.append(callback)

    def start_watching(self):
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class ConfigHandler(FileSystemEventHandler):
                def __init__(self, manager: "ConfigManager"):
                    self.manager = manager
                    self._last_modified = 0

                def on_modified(self, event):
                    if event.src_path == str(self.manager._config_path):
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
            watch_dir = str(self._config_path.parent)
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self._observer.schedule(handler, watch_dir, recursive=False)
            self._observer.start()
            print("[CONFIG] File watcher started")
        except ImportError:
            print("[CONFIG] watchdog not installed, skipping file watch")


_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
