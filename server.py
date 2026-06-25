# -*- coding: utf-8 -*-
import os
import sys
import asyncio
import json
import base64
import traceback
import secrets
import qrcode
import qrcode.image.svg
import io
from pathlib import Path
from typing import Set, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from config_manager import get_config_manager
from state_monitor import get_monitor
from action_executor import get_executor
from voice_recognizer import recognize_voice

app = FastAPI()

_use_https = False

connected_clients: Set[WebSocket] = set()
paired_devices: Set[str] = set()
pair_code = "0000"
PAIR_CODE_INTERVAL = 300

def is_admin():
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def get_local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def generate_pair_code():
    import random
    return str(random.randint(1000, 9999))

def generate_qr_text(ip, port, use_https=False):
    protocol = "https" if use_https else "http"
    return f"{protocol}://{ip}:{port}"

def _base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def _resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


@app.get("/")
async def root():
    static_path = Path(_resource_path("static")) / "index.html"
    if static_path.exists():
        content = static_path.read_text(encoding="utf-8")
        return HTMLResponse(
            content=content,
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
        )
    return HTMLResponse(content="<h1>CortexPad</h1><p>index.html not found</p>")

def _default_layout():
    return {"layout": [
        {"id": "stat_cpu", "type": "stat_cpu", "name": "CPU", "grid_x": 0, "grid_y": 0, "grid_w": 1, "grid_h": 1},
        {"id": "stat_mem", "type": "stat_mem", "name": "Memory", "grid_x": 1, "grid_y": 0, "grid_w": 1, "grid_h": 1},
        {"id": "stat_disk", "type": "stat_disk", "name": "Disk", "grid_x": 2, "grid_y": 0, "grid_w": 1, "grid_h": 1},
        {"id": "stat_gpu", "type": "stat_gpu", "name": "GPU", "grid_x": 3, "grid_y": 0, "grid_w": 1, "grid_h": 1},
        {"id": "stat_vram", "type": "stat_vram", "name": "VRAM", "grid_x": 4, "grid_y": 0, "grid_w": 1, "grid_h": 1},
        {"id": "stat_uptime", "type": "stat_uptime", "name": "Uptime", "grid_x": 5, "grid_y": 0, "grid_w": 1, "grid_h": 1},
        {"id": "btn_001", "type": "button", "name": "Mute", "icon": "volume-off", "mode": "toggle", "grid_x": 6, "grid_y": 0, "grid_w": 1, "grid_h": 1, "actions_on": [{"type": "system", "value": "mute"}], "actions_off": [{"type": "system", "value": "mute"}], "state_binding": "is_muted"},
        {"id": "btn_002", "type": "button", "name": "WeChat", "icon": "wechat", "mode": "normal", "grid_x": 7, "grid_y": 0, "grid_w": 1, "grid_h": 1, "actions": [{"type": "open", "value": "https://web.wechat.com"}]},
        {"id": "btn_vol_up", "type": "button", "name": "Vol+", "icon": "volume-up", "mode": "normal", "grid_x": 0, "grid_y": 1, "grid_w": 1, "grid_h": 1, "actions": [{"type": "system", "value": "volume_up"}]},
        {"id": "btn_vol_down", "type": "button", "name": "Vol-", "icon": "volume-down", "mode": "normal", "grid_x": 1, "grid_y": 1, "grid_w": 1, "grid_h": 1, "actions": [{"type": "system", "value": "volume_down"}]},
        {"id": "btn_bright_up", "type": "button", "name": "Bright+", "icon": "brightness-up", "mode": "normal", "grid_x": 2, "grid_y": 1, "grid_w": 1, "grid_h": 1, "actions": [{"type": "system", "value": "brightness_up"}]},
        {"id": "btn_bright_down", "type": "button", "name": "Bright-", "icon": "brightness-down", "mode": "normal", "grid_x": 3, "grid_y": 1, "grid_w": 1, "grid_h": 1, "actions": [{"type": "system", "value": "brightness_down"}]},
        {"id": "btn_voice", "type": "voice", "name": "Voice", "icon": "mic", "mode": "normal", "grid_x": 4, "grid_y": 1, "grid_w": 1, "grid_h": 1},
        {"id": "btn_media_play", "type": "button", "name": "Play/Pause", "icon": "play", "mode": "normal", "grid_x": 5, "grid_y": 1, "grid_w": 1, "grid_h": 1, "actions": [{"type": "media", "value": "play_pause"}]},
        {"id": "btn_media_prev", "type": "button", "name": "Prev", "icon": "previous", "mode": "normal", "grid_x": 6, "grid_y": 1, "grid_w": 1, "grid_h": 1, "actions": [{"type": "media", "value": "previous"}]},
        {"id": "btn_media_next", "type": "button", "name": "Next", "icon": "next", "mode": "normal", "grid_x": 7, "grid_y": 1, "grid_w": 1, "grid_h": 1, "actions": [{"type": "media", "value": "next"}]},
        {"id": "btn_win_max", "type": "button", "name": "Max", "icon": "maximize", "mode": "normal", "grid_x": 0, "grid_y": 2, "grid_w": 1, "grid_h": 1, "actions": [{"type": "window", "value": "maximize"}]},
        {"id": "btn_win_min", "type": "button", "name": "Min", "icon": "minimize", "mode": "normal", "grid_x": 1, "grid_y": 2, "grid_w": 1, "grid_h": 1, "actions": [{"type": "window", "value": "minimize"}]},
        {"id": "btn_win_left", "type": "button", "name": "Left", "icon": "window", "mode": "normal", "grid_x": 2, "grid_y": 2, "grid_w": 1, "grid_h": 1, "actions": [{"type": "window", "value": "tile_left"}]},
        {"id": "btn_win_right", "type": "button", "name": "Right", "icon": "window", "mode": "normal", "grid_x": 3, "grid_y": 2, "grid_w": 1, "grid_h": 1, "actions": [{"type": "window", "value": "tile_right"}]},
    ]}

@app.get("/api/info")
async def get_info():
    ip = get_local_ip()
    port = 8765
    url = generate_qr_text(ip, port, _use_https)
    qr_text = url
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(qr_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white", image_factory=qrcode.image.svg.SvgImage)
    svg_buf = io.BytesIO()
    img.save(svg_buf)
    svg_str = svg_buf.getvalue().decode("utf-8")
    png_img = qr.make_image(fill_color="black", back_color="white")
    png_buf = io.BytesIO()
    png_img.save(png_buf, format="PNG")
    qr_data_uri = "data:image/png;base64," + base64.b64encode(png_buf.getvalue()).decode("ascii")
    return JSONResponse(content={"url": url, "pair_code": pair_code, "ip": ip, "qr_svg": svg_str, "qr_data_uri": qr_data_uri})

@app.get("/api/admin")
async def get_admin():
    return JSONResponse(content={"is_admin": is_admin()})

@app.get("/api/pair_code")
async def get_pair_code():
    return JSONResponse(content={"pair_code": pair_code})

@app.get("/api/config")
async def get_config():
    manager = get_config_manager()
    cfg = manager.get_config()
    if "layout" not in cfg:
        cfg = _default_layout()
    return JSONResponse(content=cfg)

@app.post("/api/config")
async def save_config(config: dict):
    manager = get_config_manager()
    manager.save_config(config)
    await broadcast({"type": "config_updated", "data": config})
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    device_id = websocket.client.host if websocket.client else "unknown"

    if device_id not in paired_devices:
        try:
            await websocket.send_json({
                "type": "pair_request",
                "code_length": 4,
                "hint": "Enter the 4-digit pair code shown on your PC screen"
            })
            # Use a task-based timeout instead of asyncio.wait_for to avoid
            # leaving the WebSocket in an inconsistent state on cancellation.
            receive_task = asyncio.ensure_future(websocket.receive_json())
            done, pending = await asyncio.wait({receive_task}, timeout=30.0)
            if receive_task in pending:
                receive_task.cancel()
                try:
                    await receive_task
                except (asyncio.CancelledError, Exception):
                    pass
                print(f"[PAIR] Pairing timeout: {device_id}", flush=True)
                try:
                    await websocket.close()
                except Exception:
                    pass
                return
            response = receive_task.result()
            client_code = str(response.get("code", "")).strip()
            print(f"[PAIR] Device: {device_id}, Input: {client_code}, Expected: {pair_code}", flush=True)

            if response.get("type") == "pair_request" and client_code == pair_code:
                paired_devices.add(device_id)
                await websocket.send_json({"type": "pair_confirm", "status": "accepted"})
                print(f"[PAIR] Device paired: {device_id}", flush=True)
            else:
                await websocket.send_json({"type": "pair_confirm", "status": "rejected"})
                await websocket.close()
                return
        except WebSocketDisconnect:
            print(f"[PAIR] Client disconnected during pairing: {device_id}", flush=True)
            return
        except Exception as e:
            print(f"[PAIR] Pairing error: {device_id}, {e}", flush=True)
            traceback.print_exc()
            try:
                await websocket.close()
            except Exception:
                pass
            return

    connected_clients.add(websocket)
    print(f"[CONN] Device connected: {device_id}, Total: {len(connected_clients)}", flush=True)

    try:
        loop = asyncio.get_event_loop()
        monitor = get_monitor()
        full_state = await loop.run_in_executor(None, monitor.get_full_state)
        await websocket.send_json({"type": "state_sync", "data": full_state})

        manager = get_config_manager()
        await websocket.send_json({"type": "config_sync", "data": manager.get_config()})

        while True:
            raw = await websocket.receive()
            if raw.get("text"):
                data = json.loads(raw["text"])
                await handle_client_message(websocket, data)
            elif raw.get("bytes"):
                await _handle_voice_recognition(websocket, raw["bytes"])

    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        print(f"[CONN] Device disconnected: {device_id}, Total: {len(connected_clients)}", flush=True)
    except Exception as e:
        print(f"[WS] Error for {device_id}: {e}", flush=True)
        traceback.print_exc()
        connected_clients.discard(websocket)
        try:
            await websocket.close()
        except Exception:
            pass

async def _handle_voice_recognition(websocket: WebSocket, audio_bytes: bytes):
    try:
        import pyperclip
        text = recognize_voice(audio_bytes)
        print(f"[VOICE] Recognized: {text}", flush=True)
        if text:
            await websocket.send_json({"type": "voice_result", "text": text, "success": True})
        else:
            await websocket.send_json({"type": "voice_result", "text": "", "success": False, "error": "No speech detected"})
    except Exception as e:
        print(f"[VOICE] Error: {e}", flush=True)
        await websocket.send_json({"type": "voice_result", "text": "", "success": False, "error": str(e)})

async def _handle_voice_workflow(websocket: WebSocket, data: dict):
    workflow_id = data.get("workflow_id", "")
    text = data.get("text", "")
    print(f"[VOICE] Workflow request: {workflow_id}, text: {text}", flush=True)

    manager = get_config_manager()
    cfg = manager.get_config()
    layout = cfg.get("layout", [])
    button_map = {item.get("id", ""): item for item in layout if item.get("type") == "button"}

    matched_button = None
    text_lower = text.lower()
    for btn in layout:
        if btn.get("type") != "button":
            continue
        btn_name = btn.get("name", "").lower()
        if btn_name and btn_name in text_lower:
            matched_button = btn
            break
        btn_id = btn.get("id", "").lower()
        if btn_id and btn_id in text_lower:
            matched_button = btn
            break

    if matched_button:
        actions = matched_button.get("actions", [])
        if not actions and matched_button.get("mode") == "toggle":
            actions = matched_button.get("actions_on", [])
        if actions:
            try:
                executor = get_executor()
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(None, executor.execute_actions, actions)
                if success:
                    monitor = get_monitor()
                    state = await loop.run_in_executor(None, monitor.get_full_state)
                    await websocket.send_json({"type": "state_sync", "data": state})
                    await websocket.send_json({"type": "workflow_done", "workflow_id": workflow_id, "text": f"Executed: {matched_button.get('name', '')}"})
                else:
                    await websocket.send_json({"type": "workflow_error", "workflow_id": workflow_id, "msg": "Action execution failed"})
            except Exception as e:
                print(f"[VOICE] Action error: {e}", flush=True)
                await websocket.send_json({"type": "workflow_error", "workflow_id": workflow_id, "msg": str(e)})
        else:
            await websocket.send_json({"type": "workflow_error", "workflow_id": workflow_id, "msg": "No actions configured for this button"})
    else:
        await websocket.send_json({"type": "workflow_error", "workflow_id": workflow_id, "msg": f"No matching button found for: {text}"})

async def handle_client_message(websocket: WebSocket, data: dict):
    msg_type = data.get("type", "")

    if msg_type == "trigger":
        actions = data.get("actions", [])
        button_id = data.get("button_id", "")
        print(f"[TRIGGER] Button: {button_id}, Actions: {len(actions)}", flush=True)

        executor = get_executor()
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, executor.execute_actions, actions)

        if success:
            monitor = get_monitor()
            state = await loop.run_in_executor(None, monitor.get_full_state)
            await websocket.send_json({"type": "state_sync", "data": state})
        else:
            await websocket.send_json({"type": "error", "message": "Action failed"})

    elif msg_type == "voice_workflow":
        asyncio.create_task(_handle_voice_workflow(websocket, data))

    elif msg_type == "save_config":
        config = data.get("config", {})
        manager = get_config_manager()
        manager.save_config(config)
        await broadcast({"type": "config_updated", "data": config})
        await websocket.send_json({"type": "save_confirm", "status": "ok"})

    elif msg_type == "get_clipboard":
        monitor = get_monitor()
        clipboard = monitor._get_clipboard()
        await websocket.send_json({"type": "clipboard_sync", "data": clipboard})

    elif msg_type == "set_clipboard":
        clipboard_content = data.get("data", "")
        try:
            import pyperclip
            pyperclip.copy(clipboard_content)
            await websocket.send_json({"type": "clipboard_set", "status": "ok"})
        except Exception as e:
            await websocket.send_json({"type": "clipboard_set", "status": "error", "message": str(e)})

async def broadcast(message: dict):
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.add(client)
    connected_clients.difference_update(disconnected)

async def pair_code_rotation_loop():
    global pair_code
    while True:
        await asyncio.sleep(PAIR_CODE_INTERVAL)
        old_code = pair_code
        pair_code = f"{secrets.randbelow(10000):04d}"
        print(f"[PAIR] Pair code rotated: {old_code} -> {pair_code}", flush=True)

async def state_monitor_loop():
    monitor = get_monitor()
    loop = asyncio.get_event_loop()
    print("[MONITOR] State monitor started", flush=True)
    while True:
        await asyncio.sleep(1.0)
        # Run blocking state checks in a thread to avoid blocking the event loop
        changed = await loop.run_in_executor(None, monitor.check_state_changed)
        if changed:
            await broadcast({"type": "state_sync", "data": changed})

@app.on_event("startup")
async def startup_event():
    global pair_code
    if pair_code == "0000" or not pair_code:
        pair_code = generate_pair_code()
    ip = get_local_ip()
    port = 8765
    url = generate_qr_text(ip, port, _use_https)
    qr_text = url
    protocol = "https" if _use_https else "http"
    ws_protocol = "wss" if _use_https else "ws"

    print("", flush=True)
    print("=" * 50, flush=True)
    print("  CortexPad - Phone as Remote Controller", flush=True)
    print("=" * 50, flush=True)
    print(f"  URL:       {protocol}://{ip}:{port}", flush=True)
    print(f"  WebSocket: {ws_protocol}://{ip}:{port}/ws", flush=True)
    print(f"  Pair Code: {pair_code}", flush=True)
    print("=" * 50, flush=True)

    qr = qrcode.QRCode(version=1, box_size=1, border=1)
    qr.add_data(qr_text)
    qr.make(fit=True)

    print("", flush=True)
    print("=" * 50, flush=True)
    print("  Scan QR code to connect:", flush=True)
    print("=" * 50, flush=True)

    f = io.StringIO()
    qr.print_ascii(out=f, invert=True)
    try:
        print(f.getvalue(), flush=True)
    except (UnicodeEncodeError, UnicodeDecodeError, Exception):
        try:
            ascii_art = f.getvalue().replace(chr(0x2588), '#').replace(chr(0x2591), '.')
            print(ascii_art.encode('ascii', errors='replace').decode('ascii'), flush=True)
        except Exception:
            print('[QR code - scan from phone]', flush=True)

    print("=" * 50, flush=True)
    print("", flush=True)
    print(f"  Pair Code: {pair_code}", flush=True)
    print(f"  Enter this code on your phone to connect.", flush=True)
    print(f"  Open: {protocol}://{ip}:{port}", flush=True)
    print(f"  Press Ctrl+C to stop.", flush=True)
    print("=" * 50, flush=True)
    print("", flush=True)

    print(f"[SERVER] Pair code: {pair_code}", flush=True)

    asyncio.create_task(state_monitor_loop())
    asyncio.create_task(pair_code_rotation_loop())

def run_server():
    global _use_https
    _use_https = False
    print("[HTTP] Starting on port 8765", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")

if __name__ == "__main__":
    run_server()
