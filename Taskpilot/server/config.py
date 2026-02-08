from pathlib import Path

from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

# Project root: parent of server/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(_PROJECT_ROOT / ".env")

class Settings(BaseModel):
    groq_api_key: str = Field("", alias="GROQ_API_KEY")
    groq_model: str = Field("llama-3.1-8b-instant", alias="GROQ_MODEL")
    playwright_headless: bool = Field(False, alias="PLAYWRIGHT_HEADLESS")
    browser_timeout: int = Field(30000, alias="BROWSER_TIMEOUT")
    max_steps: int = Field(20, alias="MAX_STEPS")
    ws_frame_interval_ms: int = Field(500, alias="WS_FRAME_INTERVAL_MS")
    user_data_dir: str = Field("user-data", alias="USER_DATA_DIR")
    login_wait_ms: int = Field(60000, alias="LOGIN_WAIT_MS")
    slow_mo_ms: int = Field(0, alias="SLOW_MO_MS")

    @classmethod
    def from_env(cls):
        data = {
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
            "GROQ_MODEL": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            "PLAYWRIGHT_HEADLESS": os.getenv("PLAYWRIGHT_HEADLESS", "false"),
            "BROWSER_TIMEOUT": os.getenv("BROWSER_TIMEOUT", "30000"),
            "MAX_STEPS": os.getenv("MAX_STEPS", "20"),
            "WS_FRAME_INTERVAL_MS": os.getenv("WS_FRAME_INTERVAL_MS", "500"),
            "USER_DATA_DIR": os.getenv("USER_DATA_DIR", "user-data"),
            "LOGIN_WAIT_MS": os.getenv("LOGIN_WAIT_MS", "60000"),
            "SLOW_MO_MS": os.getenv("SLOW_MO_MS", "0"),
        }
        data["PLAYWRIGHT_HEADLESS"] = str(data["PLAYWRIGHT_HEADLESS"]).lower() in ("1", "true", "yes", "on")  # type: ignore
        user_data = data["USER_DATA_DIR"]
        if not Path(user_data).is_absolute():
            user_data = str(_PROJECT_ROOT / user_data)
        data["USER_DATA_DIR"] = user_data
        return cls(**data)  # type: ignore

settings = Settings.from_env()
