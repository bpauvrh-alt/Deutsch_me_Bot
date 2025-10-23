import os
import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update, InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask, request
from gtts import gTTS

# =====================
# Настройки
# =====================
TOKEN = os.getenv("TOKEN") or "ТВОЙ_ТОКЕН_СЮДА"
APP_URL = os.getenv("APP_URL") or "https://deutsch-me-bot.onrender.com"  # замени на свой Render URL
PORT = int(os.getenv("PORT", 5000))

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# =====================
# Данные для словаря и викторины
# =====================
vocab_list = [
    {"de": "Haus", "ru": "Дом"},
    {"de": "Hund", "ru": "Собака"},
    {"de": "Katze", "ru": "Кошка"},
]

quiz_list = [
    {"question": "Что значит 'Haus'?", "options": ["Дом", "Кошка", "Собака"], "answer": "Дом"},
    {"question": "Что значит 'Hund'?", "options": ["Кошка", "Собака", "Дом"], "answer": "Собака"},
]

# =====================
# Команды
# =====================
@dp.message(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer("👋 Привет! Я Deutsch_me_Bot 🇩🇪\n\nКоманды:\n/vocab — изучение слов\n/quiz — викторина")

@dp.message(commands=["vocab"])
async def cmd_vocab(message: types.Message):
    word = random.choice(vocab_list)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔊 Прослушать", callback_data=f"tts_{word['de']}"))
    await message.answer(f"{word['de']} — {word['ru']}", reply_markup=markup)

@dp.message(commands=["quiz"])
async def cmd_quiz(message: types.Message):
    q = random.choice(quiz_list)
    markup = InlineKeyboardMarkup()
    for opt in q["options"]:
        markup.add(InlineKeyboardButton(opt, callback_data=f"quiz_{opt}_{q['answer']}"))
    await message.answer(q["question"], reply_markup=markup)

# =====================
# Callback кнопки
# =====================
@dp.callback_query(lambda c: c.data.startswith("tts_"))
async def callback_tts(callback: types.CallbackQuery):
    word = callback.data[4:]
    tts = gTTS(text=word, lang="de")
    filename = f"audio_{word}.mp3"
    tts.save(filename)
    await callback.message.answer_audio(types.FSInputFile(filename))
    os.remove(filename)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("quiz_"))
async def callback_quiz(callback: types.CallbackQuery):
    _, selected, correct = callback.data.split("_")
    if selected == correct:
        await callback.answer("✅ Верно!")
    else:
        await callback.answer(f"❌ Неверно! Правильный ответ: {correct}")

# =====================
# Flask webhook endpoint
# =====================
@app.post(WEBHOOK_PATH)
async def webhook():
    update = Update(**request.json)
    await dp.feed_update(bot, update)
    return "ok", 200

@app.get("/")
def index():
    return "✅ Deutsch_me_Bot работает через webhook!"

# =====================
# Запуск
# =====================
async def on_startup():
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        print(f"Webhook установлен: {WEBHOOK_URL}")

def run():
    loop = asyncio.get_event_loop()
    loop.create_task(on_startup())
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    run()
