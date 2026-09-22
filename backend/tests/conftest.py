import os

# Test configuration only; no live DB is needed for the health/configuration tests.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost:5432/stay_insight_test"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
