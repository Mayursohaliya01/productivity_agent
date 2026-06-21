import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./productivity.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-change-this-before-prod")
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = int(os.getenv("TOKEN_EXPIRE_MINUTES", 1440))  # 24 hours
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    CHECKPOINT_DB: str = os.getenv("CHECKPOINT_DB", "agent_state.db")
    # DEMO — remove before production
    DEMO_SEED: bool = os.getenv("DEMO_SEED", "false").lower() in ("1", "true", "yes")


settings = Settings()
