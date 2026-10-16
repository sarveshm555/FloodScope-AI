import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env file from project root if it exists
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


class AppSettings(BaseModel):
    """Application settings and environment configuration.
    
    Safe encapsulation of environment variables ensuring credentials
    are never leaked in string representations or API schemas.
    """
    app_name: str = "FloodScope AI"
    version: str = "0.1.0"
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    api_host: str = Field(default_factory=lambda: os.getenv("API_HOST", "127.0.0.1"))
    api_port: int = Field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    frontend_url: str = Field(default_factory=lambda: os.getenv("FRONTEND_URL", "http://localhost:5173"))
    
    # Storage Configuration (configurable outside C: drive)
    data_dir_str: str = Field(default_factory=lambda: os.getenv("FLOODSCOPE_DATA_DIR", "./data"))
    
    # External Services (kept private)
    _cdse_username: Optional[str] = None
    _cdse_password: Optional[str] = None
    _cdse_client_id: Optional[str] = None
    _cdse_client_secret: Optional[str] = None
    _gemini_api_key: Optional[str] = None
    _openai_api_key: Optional[str] = None
    _llm_provider: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._cdse_username = os.getenv("CDSE_USERNAME") or None
        self._cdse_password = os.getenv("CDSE_PASSWORD") or None
        self._cdse_client_id = os.getenv("CDSE_CLIENT_ID") or None
        self._cdse_client_secret = os.getenv("CDSE_CLIENT_SECRET") or None
        self._gemini_api_key = os.getenv("GEMINI_API_KEY") or None
        self._openai_api_key = os.getenv("OPENAI_API_KEY") or None
        self._llm_provider = os.getenv("LLM_PROVIDER", "gemini")

    @property
    def data_dir(self) -> Path:
        path = Path(self.data_dir_str)
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        # Fallback to repo-relative data/ directory if configured path does not exist
        if not path.exists():
            repo_data = (PROJECT_ROOT / "data").resolve()
            if repo_data.exists():
                return repo_data
        return path

    @property
    def has_cdse_credentials(self) -> bool:
        """Indicates whether optional Copernicus Data Space credentials are configured."""
        creds = self.get_cdse_credentials()
        has_user_pass = bool(creds.get("username") and creds.get("password"))
        has_client_cred = bool(creds.get("client_id") and creds.get("client_secret"))
        return has_user_pass or has_client_cred

    @property
    def has_llm_credentials(self) -> bool:
        """Indicates whether optional LLM provider API credentials are configured."""
        if self._llm_provider == "gemini" and self._gemini_api_key:
            return True
        if self._llm_provider == "openai" and self._openai_api_key:
            return True
        return bool(self._gemini_api_key or self._openai_api_key)

    @property
    def active_llm_provider(self) -> Optional[str]:
        if self._gemini_api_key:
            return "gemini"
        if self._openai_api_key:
            return "openai"
        return None

    def get_cdse_credentials(self) -> dict:
        """Secure getter for CDSE service credentials."""
        u = os.getenv("CDSE_USERNAME") if "CDSE_USERNAME" in os.environ else self._cdse_username
        p = os.getenv("CDSE_PASSWORD") if "CDSE_PASSWORD" in os.environ else self._cdse_password
        cid = os.getenv("CDSE_CLIENT_ID") if "CDSE_CLIENT_ID" in os.environ else self._cdse_client_id
        csec = os.getenv("CDSE_CLIENT_SECRET") if "CDSE_CLIENT_SECRET" in os.environ else self._cdse_client_secret
        return {
            "username": u or None,
            "password": p or None,
            "client_id": cid or None,
            "client_secret": csec or None
        }

    def get_llm_key(self, provider: Optional[str] = None) -> Optional[str]:
        """Secure getter for LLM provider API key."""
        target = provider or self._llm_provider
        if target == "gemini":
            return self._gemini_api_key
        if target == "openai":
            return self._openai_api_key
        return self._gemini_api_key or self._openai_api_key


settings = AppSettings()
