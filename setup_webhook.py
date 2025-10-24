import os
import requests

# =====================
# Настройки
# =====================
TOKEN = "8216736672:AAHvpl2_KUk04U9ofPa5Fr4MPUwwk-XjIyk"  # твой токен
APP_URL = "https://deutsch-me-bot.onrender.com"            # твой Render URL
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

# =====================
# Удаляем старый вебхук
# =====================
delete_url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
r = requests.post(delete_url)
print("Удаление старого вебхука:", r.json())

# =====================
# Устанавливаем новый вебхук
# =====================
set_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}"
r = requests.post(set_url)
print("Установка нового вебхука:", r.json())
