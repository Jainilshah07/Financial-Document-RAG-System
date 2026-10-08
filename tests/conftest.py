import os

# Unit tests must not depend on a developer's real .env (or touch the real database).
# Real environment variables beat `.env` in pydantic-settings, so this dummy value wins.
# It must be set before `app` modules are imported, hence at conftest import time.
os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost:5432/finrag_test"
