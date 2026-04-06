import os
import ssl


def load_env_file(path: str = ".env"):
	if not os.path.exists(path):
		return

	with open(path, "r", encoding="utf-8") as env_file:
		for raw_line in env_file:
			line = raw_line.strip()
			if not line or line.startswith("#") or "=" not in line:
				continue

			key, value = line.split("=", 1)
			key = key.strip()
			value = value.strip().strip('"').strip("'")

			if key and key not in os.environ:
				os.environ[key] = value


load_env_file()

# ------------------ BOT CONFIG ------------------
# Token va adminlar ma'lumotlari
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
	raise RuntimeError("API_TOKEN is not set. Add it to .env or environment variables.")

ADMIN_ID = int(os.getenv("ADMIN_ID", "496829881"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "tezref_admin1")

# Majburiy obuna uchun bitta kanal sozlamasi
REQUIRED_CHANNEL_LINK = os.getenv("REQUIRED_CHANNEL_LINK", "https://t.me/+A4mfTNwLy5ExYTJi")
REQUIRED_CHANNEL_ID = int(os.getenv("REQUIRED_CHANNEL_ID", os.getenv("CHANNEL_ID_2", "0")))

WORK_GROUP_NAME = os.getenv("WORK_GROUP_NAME", "TezRef Official 2.0")
WORK_GROUP_LINK = os.getenv("WORK_GROUP_LINK", "")
WORK_GROUP_ID = int(os.getenv("WORK_GROUP_ID", "0"))

# ------------------ DATABASE ------------------
# PostgreSQL URL environmentdan olinadi
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
	raise RuntimeError("DATABASE_URL is not set. Add it to .env or environment variables.")

# ------------------ WEBHOOK ------------------
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")
if not WEBHOOK_BASE_URL:
	raise RuntimeError("WEBHOOK_BASE_URL is not set. Add it to .env or environment variables.")

WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/telegram/webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", API_TOKEN.split(":")[0])
WEBHOOK_URL = f"{WEBHOOK_BASE_URL.rstrip('/')}{WEBHOOK_PATH}"

WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("PORT", os.getenv("WEBAPP_PORT", "8080")))

# SSL konteksi - Railway yoki Renderga ulanish uchun kerak bo‘ladi
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
