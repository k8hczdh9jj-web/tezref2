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

# Obuna bo‘lish kerak bo‘lgan Telegram kanal usernames
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@tezrefofficial")
CHANNEL_USERNAME_2 = os.getenv("CHANNEL_USERNAME_2", "@tezrefpromo")
CHANNEL_ID_2 = int(os.getenv("CHANNEL_ID_2", "-1003276045866"))

# ------------------ DATABASE ------------------
# PostgreSQL URL environmentdan olinadi
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
	raise RuntimeError("DATABASE_URL is not set. Add it to .env or environment variables.")

# SSL konteksi - Railway yoki Renderga ulanish uchun kerak bo‘ladi
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
