# -*- coding: utf-8 -*-
"""Action interpreter - execute actions array in order"""
import os
import re
import time
import subprocess
import pyautogui
import pyperclip
from typing import Callable, Any

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


class ActionExecutor:
    def __init__(self):
        self._clipboard_backup: str = ""
        self._last_window = None

    def execute_actions(
        self,
        actions: list[dict],
        variables: dict[str, Any] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> bool:
        variables = variables or {}
        for action in actions:
            try:
                rendered_action = self._render_action(action, variables)
                action_type = rendered_action.get("type", "")
                value = rendered_action.get("value", "")

                if action_type == "hotkey":
                    self._exec_hotkey(value)
                elif action_type == "text":
                    self._exec_text(value)
                elif action_type == "open":
                    self._exec_open(value)
                elif action_type == "system":
                    self._exec_system(value)
                elif action_type == "delay":
                    self._exec_delay(value)
                elif action_type == "script":
                    self._exec_script(value)
                elif action_type == "set_volume":
                    self._set_volume(int(value))
                elif action_type == "set_brightness":
                    self._set_brightness(int(value))
                elif action_type == "wait_for_window":
                    timeout = rendered_action.get("timeout", 10)
                    settle = rendered_action.get("settle", 0.5)
                    exact = bool(rendered_action.get("exact", False))
                    self._exec_wait_for_window(value, timeout, settle, exact)
                elif action_type == "click_window":
                    self._exec_click_window(value)
                elif action_type == "media":
                    self._exec_media(value)
                elif action_type == "window":
                    self._exec_window(value)
                else:
                    msg = f"Unknown action type: {action_type}"
                    print(f"[ACTION] {msg}")
                    if on_error:
                        on_error(msg)
                    return False
            except Exception as e:
                msg = str(e)
                print(f"[ACTION] Failed [{action_type}={value}]: {msg}")
                if on_error:
                    on_error(msg)
                return False
        return True

    def _render_action(self, action: dict, variables: dict[str, Any]) -> dict:
        return {
            key: self._render_value(value, variables)
            for key, value in action.items()
        }

    def _render_value(self, value: Any, variables: dict[str, Any]) -> Any:
        if isinstance(value, str):
            return re.sub(
                r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}",
                lambda match: str(variables.get(match.group(1)) or ""),
                value,
            )
        if isinstance(value, list):
            return [self._render_value(item, variables) for item in value]
        if isinstance(value, dict):
            return {
                key: self._render_value(item, variables)
                for key, item in value.items()
            }
        return value

    def _exec_hotkey(self, value: str):
        keys = [k.strip() for k in value.split("+")]
        print(f"[ACTION] Hotkey: {'+'.join(keys)}")
        pyautogui.hotkey(*keys)

    def _exec_text(self, value: str):
        try:
            self._clipboard_backup = pyperclip.paste()
        except Exception:
            self._clipboard_backup = ""
        print(f"[ACTION] Text: {value[:30]}")
        pyperclip.copy(value)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
        try:
            pyperclip.copy(self._clipboard_backup)
        except Exception:
            pass

    def _exec_open(self, value: str):
        print(f"[ACTION] Open: {value}")
        os.startfile(value)

    def _exec_system(self, value: str):
        if value == "mute":
            self._toggle_mute()
        elif value == "shutdown":
            print("[ACTION] Shutdown")
            os.system("shutdown /s /t 0")
        elif value == "lock":
            print("[ACTION] Lock screen")
            os.system("rundll32.exe user32.dll, LockWorkStation")
        elif value == "volume_up":
            self._adjust_volume(5)
        elif value == "volume_down":
            self._adjust_volume(-5)
        elif value == "brightness_up":
            self._adjust_brightness(10)
        elif value == "brightness_down":
            self._adjust_brightness(-10)
        else:
            print(f"[ACTION] Unknown system: {value}")

    def _set_volume(self, level: int):
        """Set volume to specific level (0-100)"""
        try:
            vol = self._get_volume_interface()
            new_level = max(0.0, min(1.0, level / 100.0))
            vol.SetMasterVolumeLevelScalar(new_level, None)
            print(f"[ACTION] Set volume: {level}%")
        except Exception as e:
            print(f"[ACTION] Set volume failed: {e}")

    def _set_brightness(self, level: int):
        """Set brightness to specific level (0-100)"""
        try:
            import screen_brightness_control as sbc
            new_level = max(0, min(100, level))
            sbc.set_brightness(new_level)
            print(f"[ACTION] Set brightness: {new_level}%")
        except Exception as e:
            print(f"[ACTION] Set brightness failed: {e}")

    def _get_volume_interface(self):
        """Get volume interface using new pycaw API"""
        import comtypes
        comtypes.CoInitialize()
        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        return speakers.EndpointVolume

    def _toggle_mute(self):
        try:
            vol = self._get_volume_interface()
            current = vol.GetMute()
            vol.SetMute(not current, None)
            print(f"[ACTION] Mute: {current} -> {not current}")
        except Exception as e:
            print(f"[ACTION] Mute failed: {e}")

    def _adjust_volume(self, delta: int):
        try:
            vol = self._get_volume_interface()
            current = vol.GetMasterVolumeLevelScalar()
            new_level = max(0.0, min(1.0, current + delta / 100))
            vol.SetMasterVolumeLevelScalar(new_level, None)
            print(f"[ACTION] Volume: {int(current*100)}% -> {int(new_level*100)}%")
        except Exception as e:
            print(f"[ACTION] Volume failed: {e}")

    def _adjust_brightness(self, delta: int):
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness()
            if isinstance(current, list):
                current = current[0]
            new_level = max(0, min(100, current + delta))
            sbc.set_brightness(new_level)
            print(f"[ACTION] Brightness: {current}% -> {new_level}%")
        except Exception as e:
            print(f"[ACTION] Brightness failed (may need admin): {e}")

    def _exec_delay(self, value):
        ms = int(value)
        print(f"[ACTION] Delay: {ms}ms")
        time.sleep(ms / 1000)

    def _exec_script(self, value: str):
        print(f"[ACTION] Script: {value[:50]}")
        subprocess.Popen(value, shell=True)

    def _exec_wait_for_window(self, title_part: str, timeout, settle=0.5, exact=False):
        title_part = str(title_part or "").strip()
        timeout_seconds = float(timeout or 10)
        settle_seconds = max(0.0, float(settle or 0))
        if not title_part:
            raise RuntimeError("窗口标题不能为空")

        print(f"[ACTION] Wait for window: {title_part} ({timeout_seconds}s)")
        import pygetwindow as gw

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            for window in gw.getAllWindows():
                window_title = window.title or ""
                title_matches = window_title == title_part if exact else title_part.lower() in window_title.lower()
                if title_matches:
                    try:
                        if window.isMinimized:
                            window.restore()
                        window.activate()
                    except Exception as e:
                        print(f"[ACTION] Window focus warning: {e}")
                    self._last_window = window
                    print(f"[ACTION] Window found: {window.title}")
                    if settle_seconds:
                        print(f"[ACTION] Window settle: {settle_seconds}s")
                        time.sleep(settle_seconds)
                    return
            time.sleep(0.2)

        raise RuntimeError("窗口未找到")

    def _exec_click_window(self, value: str):
        if self._last_window is None:
            raise RuntimeError("没有可点击的目标窗口，请先执行 wait_for_window")

        parts = [p.strip().rstrip("%") for p in str(value or "50,90").split(",")]
        if len(parts) != 2:
            raise RuntimeError("click_window 的 value 应为 'x%,y%' 或 'x,y'")

        x_ratio = max(0.0, min(1.0, float(parts[0]) / 100.0))
        y_ratio = max(0.0, min(1.0, float(parts[1]) / 100.0))

        window = self._last_window
        x = int(window.left + window.width * x_ratio)
        y = int(window.top + window.height * y_ratio)
        print(f"[ACTION] Click window: {x},{y} ({parts[0]}%,{parts[1]}%)")
        pyautogui.click(x, y)
        time.sleep(0.2)

    def _exec_media(self, value: str):
        """执行媒体控制动作"""
        print(f"[ACTION] Media control: {value}")
        media_keys = {
            "play_pause": "playpause",
            "next": "nexttrack",
            "previous": "prevtrack",
            "volume_up": "volumeup",
            "volume_down": "volumedown",
            "mute": "volumemute"
        }
        if value in media_keys:
            pyautogui.press(media_keys[value])

    def _exec_window(self, value: str):
        """执行窗口管理动作"""
        print(f"[ACTION] Window control: {value}")
        window_actions = {
            "maximize": ["win", "up"],
            "minimize": ["win", "down"],
            "tile_left": ["win", "left"],
            "tile_right": ["win", "right"],
            "switch": ["alt", "tab"],
            "close": ["alt", "f4"]
        }
        if value in window_actions:
            keys = window_actions[value]
            pyautogui.hotkey(*keys)


_executor = None

def get_executor():
    global _executor
    if _executor is None:
        _executor = ActionExecutor()
    return _executor
