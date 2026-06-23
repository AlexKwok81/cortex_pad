# -*- coding: utf-8 -*-
"""CortexPad main entry"""
import os
import sys
import io
import socket
import threading
import webbrowser
import logging
import traceback
import asyncio
import uvicorn
import qrcode
import qrcode.constants
import secrets
import server
import pystray
from PIL import Image

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)), "cortexpad.log")

def _setup_logging():
    try:
        logger = logging.getLogger("cortexpad")
        logger.setLevel(logging.DEBUG)
        fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        logger = logging.getLogger("cortexpad")
    return logger

_log = _setup_logging()

def _log_exception(msg, e):
    _log.error(f"{msg}: {e}")
    _log.debug(traceback.format_exc())

sys.excepthook = lambda t, v, tb: _log_exception("Unhandled exception", v)


def is_admin():
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_admin():
    if not is_admin():
        try:
            _log.warning("Not running as admin. Some features may not work.")
            _log.info("Right-click and run as administrator for full functionality.")
        except Exception:
            pass


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _resource_path(relative_path):
    """Get path to resource - works for dev and PyInstaller onefile builds."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def create_tray_icon():
    candidates = [
        _resource_path("icon.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png"),
        os.path.join(os.getcwd(), "icon.png"),
    ]
    icon_path = None
    for p in candidates:
        if os.path.exists(p):
            icon_path = p
            break
    if not icon_path:
        _log.info("[TRAY] Using default blue icon")
        return Image.new("RGB", (16, 16), color=(0, 120, 215))
    try:
        custom_icon = Image.open(icon_path)
        if custom_icon.mode != 'RGBA':
            custom_icon = custom_icon.convert('RGBA')
        target_size = 32
        if custom_icon.size[0] != target_size or custom_icon.size[1] != target_size:
            custom_icon = custom_icon.resize((target_size, target_size), Image.LANCZOS)
        _log.info(f"[TRAY] Loaded custom icon from {icon_path}")
        return custom_icon
    except Exception as e:
        _log_exception("[TRAY] Failed to load custom icon", e)
        return Image.new("RGB", (16, 16), color=(0, 120, 215))


def on_open_browser(icon, item):
    webbrowser.open("https://127.0.0.1:8765/?qr=1")


def on_exit(icon, item):
    icon.stop()
    os._exit(0)


def _base_dir():
    """Get a writable directory for runtime data."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


_UVICORN_LOG_CFG = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"level": "WARNING", "handlers": ["null"]},
}

def run_server_thread(port):
    if not sys.stderr:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    if not sys.stdout:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")

    # Try HTTPS first
    try:
        cert_file, key_file = server._ensure_self_signed_cert()
        server._use_https = True
        _log.info(f"[HTTPS] Starting with SSL on port {port}")
        config = uvicorn.Config(
            server.app,
            host="0.0.0.0",
            port=port,
            log_level="warning",
            access_log=False,
            log_config=_UVICORN_LOG_CFG,
            ssl_certfile=cert_file,
            ssl_keyfile=key_file,
        )
        srv = uvicorn.Server(config)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(srv.serve())
        _log.info("[HTTPS] Server exited")
    except BaseException as e:
        _log_exception(f"[HTTPS] Failed ({type(e).__name__}), falling back to HTTP", e)
        server._use_https = False
        try:
            _log.info(f"[HTTP] Starting without SSL on port {port}")
            config = uvicorn.Config(
                server.app,
                host="0.0.0.0",
                port=port,
                log_level="warning",
                access_log=False,
                log_config=_UVICORN_LOG_CFG,
            )
            srv = uvicorn.Server(config)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(srv.serve())
            _log.info("[HTTP] Server exited")
        except BaseException as e2:
            _log_exception(f"[HTTP] Also failed ({type(e2).__name__})", e2)


def check_port_available(port):
    try:
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(1)
        result = test_socket.connect_ex(("0.0.0.0", port))
        test_socket.close()
        return result != 0
    except Exception:
        return True


def main():
    _log.info("CortexPad starting...")
    request_admin()
    local_ip = get_local_ip()
    port = 8765

    if not check_port_available(port):
        _log.error(f"Port {port} is already in use! Another CortexPad instance may be running.")
        import time
        time.sleep(5)
        return

    pair_code = f"{secrets.randbelow(10000):04d}"
    os.environ["CORTEXPAD_PAIR_CODE"] = pair_code
    server.pair_code = pair_code

    _log.info(f"Pair Code: {pair_code}")
    _log.info(f"URL: https://{local_ip}:{port}")

    server_thread = threading.Thread(target=run_server_thread, args=(port,), daemon=True)
    server_thread.start()

    import time
    time.sleep(3)

    if not server_thread.is_alive():
        _log.error("Server failed to start! Please check if another program is using port 8765.")
        time.sleep(3)
        return

    _log.info("Server started. Tray icon in bottom-right corner.")
    _log.info("Right-click tray icon -> Open Browser")

    icon = pystray.Icon(
        "CortexPad",
        create_tray_icon(),
        "CortexPad",
        menu=pystray.Menu(
            pystray.MenuItem("Open Browser", on_open_browser),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", on_exit),
        ),
    )

    try:
        icon.run()
    except Exception as e:
        _log_exception("[ERROR] Tray failed", e)


if __name__ == "__main__":
    main()