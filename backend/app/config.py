"""
Application configuration.

DB connection details are intentionally left blank — fill in DB_* values
in your .env file once the on-prem SQL Server is ready to connect.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    app_name: str = "DB Assistant"
    domain_description: str = "our project and resource usage database"
    example_questions: str = "\"which projects are over budget\", \"how many hours does Priya have remaining this month\""

    # --- On-prem SQL Server ---
    database_url: str = ""       # e.g. "mssql+pymssql://user:pass@server/db"

    # --- Query safety ---
    max_rows_returned: int = 200
    query_timeout_seconds: int = 10

    # --- LLM (Azure AI Foundry / Azure OpenAI - gpt-4o) ---
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""          # e.g. "https://<your-resource>.openai.azure.com"
    azure_openai_deployment: str = "gpt-4o"  # the *deployment name* in Foundry, not the base model name
    azure_openai_api_version: str = "2024-10-21"

    # --- CORS ---
    cors_origins: str = "http://localhost:5173"

    @property
    def db_configured(self) -> bool:
        return bool(self.database_url)

    @property
    def sqlalchemy_url(self) -> str:
        return self.database_url


settings = Settings()
