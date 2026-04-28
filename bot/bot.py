import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command

BOT_TOKEN = "8709959971:AAGZsyxJ3owx44uIAa5Y2NmbqSP0R-8vfTM"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz6G13Xj4LbiIcH00fsgMVxk2_6lydeaeDAzVQypHSQE5lV33GdjMG3F-_5fLQrxChs/exec"
SECRET = "arb2024secret"
WEBAPP_URL = "https://cairasan78.github.io/arb-academy/hub.html"
ADMIN_IDS = []  # вставь сюда свой Telegram ID, например [123456789]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def api(action: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(APPS_SCRIPT_URL, json={"secret": SECRET, **action}) as r:
            return await r.json()

# ── /start ──
@dp.message(Command("start"))
async def cmd_start(msg: Message):
    r = await api({"action": "check_user", "tg_id": msg.from_user.id})
    if not r.get("allowed"):
        await msg.answer("⛔️ Доступ закрыт. Обратись к администратору.")
        return

    name = r.get("display_name")
    if not name:
        await msg.answer(
            "👋 Привет! Как тебя звать?\n\n"
            "Напиши своё имя — оно будет отображаться в таблице лидеров."
        )
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎮 Открыть Академию",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]])
    await msg.answer(f"Привет, {name}! Нажми кнопку ниже 👇", reply_markup=kb)

# ── Сохранение имени ──
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(msg: Message):
    r = await api({"action": "check_user", "tg_id": msg.from_user.id})
    if not r.get("allowed"):
        return
    if r.get("display_name"):
        return  # имя уже есть, игнорируем

    name = msg.text.strip()[:32]
    await api({"action": "set_name", "tg_id": msg.from_user.id, "display_name": name})

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎮 Открыть Академию",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]])
    await msg.answer(f"Отлично, {name}! Теперь можешь играть 👇", reply_markup=kb)

# ── /allow @username ──
@dp.message(Command("allow"))
async def cmd_allow(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /allow @username")
        return

    username = parts[1].lstrip("@")
    try:
        chat = await bot.get_chat("@" + username)
        r = await api({
            "action": "add_user",
            "tg_id": chat.id,
            "tg_username": username,
            "display_name": ""
        })
        if r.get("status") == "already_exists":
            await msg.answer(f"@{username} уже в списке.")
        else:
            await msg.answer(f"✅ @{username} добавлен. При /start бот попросит имя.")
    except Exception as e:
        await msg.answer(f"❌ Не могу найти @{username}.\nОшибка: {e}")

# ── /remove @username ──
@dp.message(Command("remove"))
async def cmd_remove(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /remove @username")
        return

    username = parts[1].lstrip("@")
    try:
        chat = await bot.get_chat("@" + username)
        await api({"action": "remove_user", "tg_id": chat.id})
        await msg.answer(f"✅ @{username} удалён.")
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")

# ── /list ──
@dp.message(Command("list"))
async def cmd_list(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    r = await api({"action": "list_users"})
    users = r.get("users", [])
    if not users:
        await msg.answer("Список пуст.")
        return
    lines = [
        f"@{u['tg_username']} → {u['display_name'] or '(имя не задано)'}"
        for u in users
    ]
    await msg.answer("👥 Допущенные:\n" + "\n".join(lines))

# ── /scores ──
@dp.message(Command("scores"))
async def cmd_scores(msg: Message):
    r = await api({"action": "get_leaderboard"})
    rows = r.get("leaderboard", [])
    if not rows:
        await msg.answer("Результатов пока нет.")
        return

    games = {
        "case1":   "🔍 Кейс №1 — Ночной слив",
        "metrics": "📐 Метрики",
        "terms":   "📖 Термины"
    }
    text = "🏆 Таблица лидеров\n\n"
    for game_key, game_name in games.items():
        game_rows = sorted(
            [row for row in rows if row["game"] == game_key],
            key=lambda x: -x["score"]
        )
        if not game_rows:
            continue
        text += f"{game_name}\n"
        medals = ["🥇", "🥈", "🥉", "4.", "5."]
        for i, row in enumerate(game_rows[:5]):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            text += f"  {medal} {row['name']} — {row['score']}/{row['total']}\n"
        text += "\n"

    await msg.answer(text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
