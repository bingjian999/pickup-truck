import os
from dataclasses import dataclass, field
from typing import Optional

def _load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key, value = key.strip(), value.strip()
                    if key and key not in os.environ:
                        os.environ[key] = value

_load_dotenv()

@dataclass
class Config:
    pdf_path: str = r"D:\Software\聊天记录\xwechat_files\q466717119_fe08\msg\file\2026-02\InternationalGAAP®2025_compressed.pdf"
    output_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

    openai_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY"))
    openai_api_base: Optional[str] = field(default_factory=lambda: os.environ.get("OPENAI_API_BASE"))
    openai_model: str = field(default_factory=lambda: os.environ.get("OPENAI_MODEL", "gpt-4o"))

    translation_chunk_size: int = 2000
    translation_chunk_overlap: int = 200
    translation_max_concurrent: int = 5

    checkpoint_interval: int = 10

    chapters_to_process: Optional[list] = None
    skip_existing: bool = True

    def __post_init__(self):
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "chapters", "en"), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "chapters", "zh"), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "chapters", "bilingual"), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "full"), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "checkpoints"), exist_ok=True)