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
        """Transcribe audio from in-memory bytes via temp file.
        Auto-detects format: webm/ogg containers vs raw PCM/WAV.
        """
        # Detect format by magic bytes
        if audio_bytes[:4] == b'RIFF':
            suffix = ".wav"
        elif audio_bytes[:4] in (b'\x1aE\xdf\xa3', b'OggS'):
            suffix = ".webm"
        else:
            # Assume webm (from MediaRecorder) or raw PCM - try webm first
            suffix = ".webm"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        try:
            return self.transcribe_from_path(tmp_path)
        except Exception as e:
            # If webm failed, the bytes might be raw PCM - save as wav and retry
            if suffix == ".webm":
                import struct
                try:
                    # Try interpreting as Float32 PCM (from voice_input)
                    num_samples = len(audio_bytes) // 4
                    if num_samples > 4410:  # >0.1s at 44100Hz
                        import wave
                        wav_path = tmp_path + ".wav"
                        with wave.open(wav_path, 'wb') as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)  # 16-bit
                            wf.setframerate(44100)
                            # Convert float32 to int16
                            floats = struct.unpack(f'{num_samples}f', audio_bytes[:num_samples*4])
                            ints = [max(-32768, min(32767, int(s * 32767))) for s in floats]
                            wf.writeframes(struct.pack(f'{len(ints)}h', *ints))
                        result = self.transcribe_from_path(wav_path)
                        os.unlink(wav_path)
                        return result
                except Exception:
                    pass
            raise e
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
