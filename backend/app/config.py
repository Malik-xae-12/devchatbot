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

    # --- On-prem SQL Server (fill these in later) ---
    db_server: str = ""          # e.g. "SQLPROD01" or "10.0.0.5,1433"
    db_name: str = ""
    # Set true to use Windows Authentication (Trusted_Connection) instead of
    # a SQL login — typical for a dev box where you're already domain-joined
    # and have been granted read access under your own Windows account.
    # When true, db_user/db_password are ignored.
    db_use_windows_auth: bool = False
    db_user: str = ""
    db_password: str = ""
    db_driver: str = "ODBC Driver 18 for SQL Server"
    db_encrypt: bool = True
    db_trust_server_certificate: bool = False
    db_read_only: bool = True

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
        if self.db_use_windows_auth:
            return bool(self.db_server and self.db_name)
        return bool(self.db_server and self.db_name and self.db_user)

    @property
    def sqlalchemy_url(self) -> str:
        import urllib.parse
        driver_encoded = self.db_driver.replace(" ", "+")
        password_encoded = urllib.parse.quote_plus(self.db_password) if self.db_password else ""
        if self.db_use_windows_auth:
            return (
                f"mssql+pyodbc://@{self.db_server}/{self.db_name}?driver={driver_encoded}"
                f"&trusted_connection=yes"
                f"&Encrypt={'yes' if self.db_encrypt else 'no'}"
                f"&TrustServerCertificate={'yes' if self.db_trust_server_certificate else 'no'}"
            )
        return (
            f"mssql+pyodbc://{self.db_user}:{password_encoded}"
            f"@{self.db_server}/{self.db_name}?driver={driver_encoded}"
            f"&Encrypt={'yes' if self.db_encrypt else 'no'}"
            f"&TrustServerCertificate={'yes' if self.db_trust_server_certificate else 'no'}"
        )


settings = Settings()
