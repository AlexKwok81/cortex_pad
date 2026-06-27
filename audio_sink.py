# -*- coding: utf-8 -*-
"""
audio_sink.py - VB-Cable virtual audio output sink.

Writes Float32 PCM audio data to a VB-Cable "CABLE Input" playback device,
which is then picked up by applications (e.g. WeChat IME) listening on
"CABLE Output".

Requires: PyAudio, numpy, VB-Cable virtual audio driver installed.
"""
import threading
import numpy as np
import pyaudio

SAMPLE_RATE = 44100
CHANNELS = 1
FORMAT = pyaudio.paFloat32
FRAMES_PER_BUFFER = 4096


class AudioSink:
    def __init__(self):
        self._pa = pyaudio.PyAudio()
        self._stream = None
        self._lock = threading.Lock()
        self._device_index = self._find_cable_input_index()

    def _find_cable_input_index(self):
        target_keywords = [
            "cable input",
            "virtual-audio-cable",
            "vb-audio virtual cable",
            "vb-cable",
            "cable",
        ]
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            name = (info.get("name") or "").lower()
            is_output = int(info.get("maxOutputChannels", 0)) > 0
            if is_output and any(kw in name for kw in target_keywords):
                return i
        return None

    @property
    def available(self) -> bool:
        return self._device_index is not None

    @property
    def device_name(self) -> str:
        if self._device_index is None:
            return ""
        return self._pa.get_device_info_by_index(self._device_index).get("name", "")

    def start(self):
        with self._lock:
            if self._stream is not None:
                return
            if self._device_index is None:
                raise RuntimeError("CABLE Input device not found")

            self._stream = self._pa.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True,
                output_device_index=self._device_index,
                frames_per_buffer=FRAMES_PER_BUFFER,
            )

    def stop(self):
        with self._lock:
            if self._stream is None:
                return
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            finally:
                self._stream = None

    def write(self, raw_bytes: bytes):
        if not raw_bytes:
            return
        with self._lock:
            if self._stream is None:
                return
            try:
                audio = np.frombuffer(raw_bytes, dtype=np.float32)
                if audio.ndim != 1:
                    audio = audio.reshape(-1)
                self._stream.write(audio.astype(np.float32).tobytes())
            except Exception:
                pass


_audio_sink = None


def get_audio_sink() -> AudioSink:
    global _audio_sink
    if _audio_sink is None:
        _audio_sink = AudioSink()
    return _audio_sink