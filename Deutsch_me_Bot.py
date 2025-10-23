import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputFile
from aiogram.filters import Command
from gtts import gTTS
from io import BytesIO
import random
from flask import Flask
import threading

# ==== НАСТРОЙКИ ====
API_TOKEN = "8216736672:AAHvpl2_KUk04U9ofPa5Fr4MPUwwk-XjIyk"  # <-- вставь свой токен
DB_FILE = "german_bot.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
quiz_data = {}
last_vocab_id = None

# ==== Flask для Uptime Robot ====
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=5000)  # порт 5000, чтобы 8080 не конфликтовал

threading.Thread(target=run_flask, daemon=True).start()

# ==== ИНИЦИАЛИЗАЦИЯ БД ====
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS vocab (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT,
            translation TEXT,
            example TEXT
        )""")
        cur = await db.execute("SELECT COUNT(*) FROM vocab")
        count = (await cur.fetchone())[0]
        if count == 0:
            sample = [
                ("Guten Morgen", "Доброе утро", "Guten Morgen! Wie geht's?"),
                ("Danke", "Спасибо", "Danke für deine Hilfe."),
                ("Bitte", "Пожалуйста", "Bitte sehr."),
                ("Entschuldigung", "Извините", "Entschuldigung, wo ist die Toilette?"),
            ]
            await db.executemany("INSERT INTO vocab (word, translation, example) VALUES (?, ?, ?)", sample)
        await db.commit()

# ==== ПОЛУЧЕНИЕ СЛУЧАЙНОГО СЛОВА ====
async def get_random_vocab(exclude_id=None):
    async with aiosqlite.connect(DB_FILE) as db:
        if exclude_id:
            cur = await db.execute(
                "SELECT id, word, translation, example FROM vocab WHERE id != ? ORDER BY RANDOM() LIMIT 1",
                (exclude_id,)
            )
        else:
            cur = await db.execute(
                "SELECT id, word, translation, example FROM vocab ORDER BY RANDOM() LIMIT 1"
            )
        row = await cur.fetchone()
        return row

# ==== ГЕНЕРАЦИЯ TTS в памяти ====
def make_tts_bytes(word):
    tts = gTTS(text=word, lang="de")
    bio = BytesIO()
    tts.write_to_fp(bio)
    bio.seek(0)
    return bio

# ==== /start ====
@dp.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        "👋 Привет! Я — *Deutsch_me_Bot*, бот для изучения немецкого 🇩🇪.\n\n"
        "Доступные команды:\n"
        "• /vocab — карточка слова с озвучкой\n"
        "• /quiz — небольшая викторина\n"
        "• /help — справка"
    )
    await message.answer(text, parse_mode="Markdown")

# ==== /help ====
@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("📚 Команды:\n/start — начать\n/vocab — карточка слова с озвучкой\n/quiz — викторина")

# ==== /vocab с озвучкой ====
@dp.message(Command("vocab"))
async def cmd_vocab(message: Message):
    global last_vocab_id
    vocab = await get_random_vocab(exclude_id=last_vocab_id)
    if not vocab:
        await message.answer("Слова не найдены 😢")
        return

    vid, word, translation, example = vocab
    last_vocab_id = vid

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Следующее", callback_data="next")]
    ])

    text = f"**{word}** — {translation}\n\n_Пример:_ {example}"
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)

    tts_audio = make_tts_bytes(word)
    await message.answer_audio(InputFile(tts_audio, filename=f"{word}.mp3"), caption=f"🎧 {word}")

# ==== Кнопка "Следующее" ====
@dp.callback_query(F.data == "next")
async def callback_next(call: CallbackQuery):
    await call.answer()
    await cmd_vocab(call.message)

# ==== /quiz ====
@dp.message(Command("quiz"))
async def cmd_quiz(message: Message):
    async with aiosqlite.connect(DB_FILE) as db:
        cur = await db.execute("SELECT id, word, translation FROM vocab ORDER BY RANDOM() LIMIT 1")
        row = await cur.fetchone()
        if not row:
            await message.answer("Нет слов для викторины.")
            return
        vid, word, correct = row
        cur = await db.execute("SELECT translation FROM vocab WHERE id != ? ORDER BY RANDOM() LIMIT 3", (vid,))
        options = [correct] + [r[0] for r in await cur.fetchall()]

    random.shuffle(options)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=opt, callback_data=f"ans:{vid}:{i}")] for i, opt in enumerate(options)
    ])

    quiz_data[f"quiz_{vid}"] = {"options": options, "correct": correct}
    await message.answer(f"Что значит слово *{word}*?", parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data.startswith("ans:"))
async def callback_answer(call: CallbackQuery):
    _, vid, idx = call.data.split(":")
    vid = int(vid)
    idx = int(idx)
    data = quiz_data.get(f"quiz_{vid}")
    if not data:
        await call.message.answer("Ошибка викторины 😢")
        await call.answer()
        return

    chosen = data["options"][idx]
    correct = data["correct"]

    if chosen == correct:
        await call.message.answer("✅ Правильно!")
    else:
        await call.message.answer(f"❌ Неверно. Правильный ответ: {correct}")
    await call.answer()

# ==== ЗАПУСК ====
async def main():
    await init_db()
    print("Бот запущен на сервере ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())