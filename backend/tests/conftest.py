import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{(ROOT / 'data' / 'test_sentinel.db').as_posix()}")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("WEBHOOK_TOKEN", "test-webhook")
os.environ.setdefault("OPENAI_API_KEY", "")
