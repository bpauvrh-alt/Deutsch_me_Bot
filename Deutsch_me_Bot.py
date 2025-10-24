import os
import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update, InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask, request
from gtts import gTTS

# ========== Настройки ==========
TOKEN = os.getenv("TOKEN") or "ТВОЙ_ТОКЕН_СЮДА"
APP_URL = os.getenv("APP_URL") or "https://deutsch-me-bot.onrender.com"
PORT = int(os.getenv("PORT", 5000))

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# ========== Данные ==========
vocab_list = [
    {"de": "Haus", "ru": "Дом"},
    {"de": "Hund", "ru": "Собака"},
    {"de": "Katze", "ru": "Кошка"},
]
quiz_list = [
    {"question": "Что значит 'Haus'?", "options": ["Дом", "Кошка", "Собака"], "answer": "Дом"},
    {"question": "Что значит 'Hund'?", "options": ["Кошка", "Собака", "Дом"], "answer": "Собака"},
]

# ========== Команды ==========
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

# ========== Callback кнопки ==========
@dp.callback_query(lambda c: c.data and c.data.startswith("tts_"))
async def callback_tts(callback: types.CallbackQuery):
    word = callback.data[4:]
    tts = gTTS(text=word, lang="de")
    filename = f"audio_{word}.mp3"
    tts.save(filename)
    await callback.message.answer_audio(types.FSInputFile(filename))
    try:
        os.remove(filename)
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("quiz_"))
async def callback_quiz(callback: types.CallbackQuery):
    _, selected, correct = callback.data.split("_", 2)
    if selected == correct:
        await callback.answer("✅ Верно!")
    else:
        await callback.answer(f"❌ Неверно! Правильный ответ: {correct}")

# ========== Flask webhook endpoint ==========
# Сделаем синхронный обработчик: поставим задачу в asyncio loop
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update(**data)
    # ставим в очередь обработки в asyncio loop
    asyncio.get_event_loop().create_task(dp.process_update(update))
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "✅ Deutsch_me_Bot работает через webhook!", 200

# ========== Установка webhook при старте ==========
async def on_startup():
    # проверяем webhook info и устанавливаем, если нужно
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        print(f"Webhook установлен: {WEBHOOK_URL}")
    else:
        print("Webhook уже установлен:", webhook_info.url)

def run():
    # здесь мы синхронно запускаем on_startup(), чтобы webhook точно установился
    loop = asyncio.get_event_loop()
    loop.run_until_complete(on_startup())
    # затем запускаем Flask (blocking)
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    run()