# -*- coding: utf-8 -*-
"""Voice recognition module using faster-whisper (Whisper base model, CPU int8, Chinese)."""
import io
import os
import tempfile
from pathlib import Path

# Model cache directory - avoid C drive per project requirements
_MODELS_DIR = Path(__file__).parent / "models" / "whisper"

_recognizer = None


class VoiceRecognizer:
    def __init__(self):
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            os.makedirs(_MODELS_DIR, exist_ok=True)
            # Auto-detect GPU availability
            device = "cpu"
            compute_type = "int8"
            try:
                import ctranslate2
                if ctranslate2.get_supported_compute_types("cuda"):
                    device = "cuda"
                    compute_type = "float16"
            except Exception:
                pass
            print(f"[VOICE] Loading whisper small model on {device} ({compute_type})...", flush=True)
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                "small",
                device=device,
                compute_type=compute_type,
                download_root=str(_MODELS_DIR),
            )
            print(f"[VOICE] Whisper model loaded on {device}", flush=True)

    @property
    def model_loaded(self):
        return self._model is not None

    def transcribe_from_path(self, audio_path: str) -> str:
        """Transcribe audio file and return recognized text."""
        self._ensure_model()
        segments, _info = self._model.transcribe(
            audio_path,
            language="zh",
            beam_size=5,
        )
        parts = [seg.text.strip() for seg in segments if seg.text.strip()]
        return "".join(parts)

    def transcribe_from_bytes(self, audio_bytes: bytes) -> str:
        """Transcribe audio from in-memory bytes via temp file."""
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        try:
            return self.transcribe_from_path(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def get_voice_recognizer() -> VoiceRecognizer:
    global _recognizer
    if _recognizer is None:
        _recognizer = VoiceRecognizer()
    return _recognizer


def recognize_voice(audio_bytes: bytes) -> str:
    """Module-level helper: transcribe audio bytes, return text."""
    return get_voice_recognizer().transcribe_from_bytes(audio_bytes)
