import os
import sys

# Ensure project root is on sys.path for 'import app'
ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Default environment variables for tests
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret")

# Load additional fixtures and Celery configuration from the app package
import app.conftest  # noqa: F401
