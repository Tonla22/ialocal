"""Optional offline STT adapter. No model or package is downloaded on request."""
import importlib.util
from ..config import config

def available():
    return config.voice_enabled and config.path(config.stt_model_path).is_dir() and importlib.util.find_spec('faster_whisper') is not None

def transcribe(path):
    from faster_whisper import WhisperModel
    model = WhisperModel(str(config.path(config.stt_model_path)), device='cpu', compute_type='int8', local_files_only=True)
    segments, _ = model.transcribe(str(path), language='es', beam_size=1)
    return ' '.join(segment.text for segment in segments)
