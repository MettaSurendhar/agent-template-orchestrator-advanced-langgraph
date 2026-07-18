"""Points the app at a temp/test Postgres database before any test module imports it.

pytest_configure runs before test collection/imports, so setting env vars here
guarantees `api.__init__`'s `Settings()` (which reads env vars at import time) picks up
the test DB instead of the real `.env` defaults.
"""

import os


def pytest_configure(config):
    dsn = "postgresql://postgres:postgres@localhost:5432/orchestrator_advanced_test?sslmode=disable"
    os.environ["DATABASE_URL"] = dsn
    os.environ["CHECKPOINT_DATABASE_URL"] = dsn
    os.environ["JWT_SECRET"] = "test-secret-do-not-use-in-prod"
    os.environ["DEFAULT_TEAM_ID"] = "default-team-test"
