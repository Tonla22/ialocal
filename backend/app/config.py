from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]

class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    app_origin: str = 'http://127.0.0.1:8765'
    ollama_url: str = 'http://localhost:11434'
    ollama_model: str = 'qwen3:8b'
    database_path: str = 'data/assistant.sqlite3'
    authorized_roots: str = 'data/workspace'
    session_secure: bool = False
    session_hours: int = 12
    ollama_timeout: int = 240
    max_iterations: int = 6
    stt_model_path: str = 'data/models/whisper'
    voice_enabled: bool = False
    vision_enabled: bool = True
    computer_control_enabled: bool = False

    def path(self, value: str) -> Path:
        path = Path(value)
        return (path if path.is_absolute() else ROOT / path).resolve()

    @property
    def roots(self):
        return [self.path(x.strip()) for x in self.authorized_roots.split(';') if x.strip()]

config = Config()
