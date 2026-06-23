# -*- coding: utf-8 -*-
"""System state monitor - periodically check volume/brightness/processes"""
import time
import psutil
from typing import Optional, Set


class StateMonitor:
    def __init__(self):
        self._last_state: dict = {}
        self._last_process_check: float = 0
        self._process_interval: float = 3.0
        self._last_volume_check: float = 0
        self._last_system_check: float = 0
        self._system_interval: float = 2.0  # 每2秒检查一次系统指标
        self._last_clipboard: str = ""
        self._last_clipboard_check: float = 0
        self._clipboard_interval: float = 1.0  # 每1秒检查一次剪贴板

    def get_full_state(self) -> dict:
        state = {
            "volume": self._get_volume(),
            "is_muted": self._is_muted(),
            "brightness": self._get_brightness(),
            "running_apps": self._get_running_apps(),
            "cpu_percent": self._get_cpu(),
            "memory_percent": self._get_memory(),
            "memory_used_gb": self._get_memory_used(),
            "memory_total_gb": self._get_memory_total(),
            "disk_percent": self._get_disk(),
            "disk_used_gb": self._get_disk_used(),
            "disk_total_gb": self._get_disk_total(),
            "uptime_hours": self._get_uptime(),
            "gpu_percent": self._get_gpu(),
            "vram_used_gb": self._get_vram_used(),
            "vram_total_gb": self._get_vram_total(),
            "clipboard": self._get_clipboard()
        }
        self._last_state = state.copy()
        return state

    def check_state_changed(self) -> Optional[dict]:
        now = time.time()
        changed = False
        new_state = self._last_state.copy()

        if now - self._last_volume_check >= 1.0:
            self._last_volume_check = now
            vol = self._get_volume()
            mute = self._is_muted()
            if vol != new_state.get("volume") or mute != new_state.get("is_muted"):
                new_state["volume"] = vol
                new_state["is_muted"] = mute
                changed = True

        bright = self._get_brightness()
        if bright != new_state.get("brightness"):
            new_state["brightness"] = bright
            changed = True

        if now - self._last_process_check >= self._process_interval:
            self._last_process_check = now
            apps = self._get_running_apps()
            if apps != new_state.get("running_apps"):
                new_state["running_apps"] = apps
                changed = True

        # 定期检查系统指标（CPU、GPU、显存、内存、磁盘）
        if now - self._last_system_check >= self._system_interval:
            self._last_system_check = now
            cpu = self._get_cpu()
            mem = self._get_memory()
            mem_used = self._get_memory_used()
            mem_total = self._get_memory_total()
            disk = self._get_disk()
            disk_used = self._get_disk_used()
            disk_total = self._get_disk_total()
            gpu = self._get_gpu()
            vram_used = self._get_vram_used()
            vram_total = self._get_vram_total()
            
            if (cpu != new_state.get("cpu_percent") or
                mem != new_state.get("memory_percent") or
                mem_used != new_state.get("memory_used_gb") or
                mem_total != new_state.get("memory_total_gb") or
                disk != new_state.get("disk_percent") or
                disk_used != new_state.get("disk_used_gb") or
                disk_total != new_state.get("disk_total_gb") or
                gpu != new_state.get("gpu_percent") or
                vram_used != new_state.get("vram_used_gb") or
                vram_total != new_state.get("vram_total_gb")):
                new_state["cpu_percent"] = cpu
                new_state["memory_percent"] = mem
                new_state["memory_used_gb"] = mem_used
                new_state["memory_total_gb"] = mem_total
                new_state["disk_percent"] = disk
                new_state["disk_used_gb"] = disk_used
                new_state["disk_total_gb"] = disk_total
                new_state["gpu_percent"] = gpu
                new_state["vram_used_gb"] = vram_used
                new_state["vram_total_gb"] = vram_total
                changed = True

        # 检查剪贴板变化
        if now - self._last_clipboard_check >= self._clipboard_interval:
            self._last_clipboard_check = now
            clipboard = self._get_clipboard()
            if clipboard != new_state.get("clipboard"):
                new_state["clipboard"] = clipboard
                changed = True

        if changed:
            self._last_state = new_state.copy()
            return new_state
        return None

    def _get_volume_interface(self):
        """Get volume interface using new pycaw API"""
        import comtypes
        comtypes.CoInitialize()
        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        return speakers.EndpointVolume

    def _get_volume(self) -> int:
        try:
            vol = self._get_volume_interface()
            return int(vol.GetMasterVolumeLevelScalar() * 100)
        except Exception:
            return 0

    def _is_muted(self) -> bool:
        try:
            vol = self._get_volume_interface()
            return bool(vol.GetMute())
        except Exception:
            return False

    def _get_brightness(self) -> int:
        try:
            import screen_brightness_control as sbc
            brightness = sbc.get_brightness()
            if isinstance(brightness, list):
                brightness = brightness[0]
            return int(brightness)
        except Exception:
            return 50

    def _get_cpu(self) -> float:
        try:
            return psutil.cpu_percent(interval=0)
        except Exception:
            return 0.0

    def _get_memory(self) -> float:
        try:
            return psutil.virtual_memory().percent
        except Exception:
            return 0.0

    def _get_memory_used(self) -> float:
        try:
            return round(psutil.virtual_memory().used / (1024**3), 1)
        except Exception:
            return 0.0

    def _get_memory_total(self) -> float:
        try:
            return round(psutil.virtual_memory().total / (1024**3), 1)
        except Exception:
            return 0.0

    def _get_disk(self) -> float:
        try:
            return psutil.disk_usage('C:\\').percent
        except Exception:
            return 0.0

    def _get_disk_used(self) -> float:
        try:
            return round(psutil.disk_usage('C:\\').used / (1024**3), 1)
        except Exception:
            return 0.0

    def _get_disk_total(self) -> float:
        try:
            return round(psutil.disk_usage('C:\\').total / (1024**3), 1)
        except Exception:
            return 0.0

    def _get_uptime(self) -> float:
        try:
            boot = psutil.boot_time()
            import time
            return round((time.time() - boot) / 3600, 1)
        except Exception:
            return 0.0

    def _get_gpu(self) -> float:
        try:
            import subprocess
            out = subprocess.check_output(["nvidia-smi","--query-gpu=utilization.gpu","--format=csv,noheader,nounits"], encoding="utf-8").strip()
            return float(out.split(",")[0].strip())
        except Exception:
            return 0.0

    def _get_vram_used(self) -> float:
        try:
            import subprocess
            out = subprocess.check_output(["nvidia-smi","--query-gpu=memory.used,memory.total","--format=csv,noheader,nounits"], encoding="utf-8").strip()
            parts = out.split(",")
            return round(float(parts[0].strip()) / 1024, 1)
        except Exception:
            return 0.0

    def _get_vram_total(self) -> float:
        try:
            import subprocess
            out = subprocess.check_output(["nvidia-smi","--query-gpu=memory.used,memory.total","--format=csv,noheader,nounits"], encoding="utf-8").strip()
            parts = out.split(",")
            return round(float(parts[1].strip()) / 1024, 1)
        except Exception:
            return 0.0

    def _get_running_apps(self) -> list:
        try:
            apps: Set[str] = set()
            for proc in psutil.process_iter(["name"]):
                try:
                    name = proc.info["name"]
                    if name and not name.startswith(("System", "Idle", "Registry", "svchost")):
                        apps.add(name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return sorted(list(apps))
        except Exception:
            return []

    def _get_clipboard(self) -> str:
        """获取当前剪贴板内容"""
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception:
            return ""


_monitor = None

def get_monitor():
    global _monitor
    if _monitor is None:
        _monitor = StateMonitor()
    return _monitor
