import os

# BAD: debug mode exposes Werkzeug interactive debugger on errors
DEBUG = True

# BAD: hardcoded weak secret key
SECRET_KEY = "supersecretkey123"

# BAD: hardcoded database credentials
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://admin:password123@localhost/appdb"
)
