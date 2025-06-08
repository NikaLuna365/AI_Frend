import os
import sys

# Ensure Python path includes project root for `import app`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure JWT secret for tests
os.environ.setdefault('JWT_SECRET_KEY', 'test-secret')

import app.conftest  # noqa: F401
