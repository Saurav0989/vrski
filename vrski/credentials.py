"""
Credential store for Vrski — reads and writes Google account details to .env.

Agents call save_credentials() once (after asking the owner). All subsequent
signin calls read from the .env automatically via load_credentials().
"""
import os
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("vrski.credentials")

# .env lives at the project root (one level above this package)
_ENV_PATH = Path(__file__).parent.parent / ".env"

_EMAIL_KEY = "VRSKI_GOOGLE_EMAIL"
_PASSWORD_KEY = "VRSKI_GOOGLE_PASSWORD"


def _ensure_dotenv():
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_PATH, override=False)
    except ImportError:
        pass


def save_credentials(email: str, password: str) -> None:
    """Persist Google credentials to .env. Overwrites any existing values."""
    try:
        from dotenv import set_key
        _ENV_PATH.touch(exist_ok=True)
        set_key(str(_ENV_PATH), _EMAIL_KEY, email)
        set_key(str(_ENV_PATH), _PASSWORD_KEY, password)
        logger.info(f"Credentials saved for {email}")
    except ImportError:
        # Fallback: write manually if python-dotenv not installed yet
        lines = []
        if _ENV_PATH.exists():
            for line in _ENV_PATH.read_text().splitlines():
                if not line.startswith(_EMAIL_KEY) and not line.startswith(_PASSWORD_KEY):
                    lines.append(line)
        lines.append(f'{_EMAIL_KEY}="{email}"')
        lines.append(f'{_PASSWORD_KEY}="{password}"')
        _ENV_PATH.write_text("\n".join(lines) + "\n")
        logger.info(f"Credentials saved (fallback write) for {email}")


def load_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Return (email, password) from .env or environment, or (None, None)."""
    _ensure_dotenv()
    email = os.environ.get(_EMAIL_KEY) or os.getenv(_EMAIL_KEY)
    password = os.environ.get(_PASSWORD_KEY) or os.getenv(_PASSWORD_KEY)
    return email or None, password or None


def has_credentials() -> bool:
    email, password = load_credentials()
    return bool(email and password)


def get_email() -> Optional[str]:
    email, _ = load_credentials()
    return email
