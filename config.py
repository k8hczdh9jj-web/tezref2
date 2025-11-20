import os
import ssl

# ------------------ BOT CONFIG ------------------
# Token va adminlar ma'lumotlari
API_TOKEN = "8401942831:AAF7rQa6UC7YGNyIk9gdx1XnaiyxZlt5lJA"
ADMIN_ID = 496829881
ADMIN_USERNAME = "tezref_admin1"

# Obuna bo‘lish kerak bo‘lgan Telegram kanal usernames
CHANNEL_USERNAME = "@tezrefofficial"
CHANNEL_USERNAME_2 = '@tezrefpromo'

# ------------------ DATABASE ------------------
# PostgreSQL URL environmentdan olinadi
DATABASE_URL = os.getenv("DATABASE_URL")

# SSL konteksi - Railway yoki Renderga ulanish uchun kerak bo‘ladi
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
