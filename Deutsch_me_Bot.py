import os
import asyncio
import random
import json
from urllib.parse import quote

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask, request
from gtts import gTTS
import pathlib

# =====================
# Настройки
# =====================
TOKEN = os.getenv("TOKEN") or "ТВОЙ_ТОКЕН_СЮДА"
APP_URL = os.getenv("APP_URL") or "https://deutsch-me-bot.onrender.com"
PORT = int(os.getenv("PORT", 5000))

# URL кодируем токен на случай спецсимволов
WEBHOOK_PATH = f"/webhook/{quote(TOKEN)}"
WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = Flask(__name__)

# =====================
# Загружаем слова и викторины из JSON
# =====================
BASE_DIR = pathlib.Path(__file__).parent
with open(BASE_DIR / "danish_vocab.json", encoding="utf-8") as f:
    data = json.load(f)

vocab_list = data.get("vocab", [])
quiz_list = data.get("quiz", [])

# =====================
# Команды
# =====================
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я Danish Trainer 🇩🇰\n\nКоманды:\n"
        "/vocab — изучение слов\n"
        "/quiz — викторина"
    )

@dp.message_handler(commands=["vocab"])
async def cmd_vocab(message: types.Message):
    word = random.choice(vocab_list)
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            "🔊 Прослушать",
            callback_data=f"tts_{word['da']}"
        )
    )
    await message.answer(f"{word['da']} — {word['ru']}", reply_markup=markup)

@dp.message_handler(commands=["quiz"])
async def cmd_quiz(message: types.Message):
    q = random.choice(quiz_list)
    markup = InlineKeyboardMarkup()
    for opt in q["options"]:
        # Используем "|" как безопасный разделитель
        markup.add(
            InlineKeyboardButton(opt, callback_data=f"quiz_{opt}|{q['answer']}")
        )
    await message.answer(q["question"], reply_markup=markup)

# =====================
# Callback кнопки
# =====================
@dp.callback_query_handler(lambda c: c.data.startswith("tts_"))
async def callback_tts(callback: types.CallbackQuery):
    word = callback.data[4:]
    tts = gTTS(text=word, lang="da")
    filename = f"audio_{word}.mp3"
    tts.save(filename)
    with open(filename, "rb") as audio:
        await bot.send_audio(chat_id=callback.message.chat.id, audio=audio)
    os.remove(filename)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("quiz_"))
async def callback_quiz(callback: types.CallbackQuery):
    _, payload = callback.data.split("_")
    selected, correct = payload.split("|")
    if selected == correct:
        await callback.answer("✅ Верно!")
    else:
        await callback.answer(f"❌ Неверно! Правильный ответ: {correct}")

# =====================
# Flask webhook endpoint
# =====================
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = types.Update(**request.json)
    asyncio.create_task(dp.feed_update(bot, update))
    return "OK"

@app.route("/")
def index():
    return "✅ Danish Trainer работает через webhook!"

# =====================
# Запуск
# =====================
if __name__ == "__main__":
    async def on_startup():
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url != WEBHOOK_URL:
            await bot.set_webhook(WEBHOOK_URL)
            print(f"Webhook установлен: {WEBHOOK_URL}")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(on_startup())
    app.run(host="0.0.0.0", port=PORT)