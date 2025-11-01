from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import os
import asyncpg

# 🔑 TOKEN VA ADMIN ID
API_TOKEN = "8520385805:AAHjOr3ThLFwjLepdS_9hNupgtwvg-tlALI"
ADMIN_ID = 496829881  # Admin Telegram ID

# 🔧 Bot sozlamalari
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# 🌐 Postgres DATABASE_URL (Heroku dan olinadi)
DATABASE_URL = os.getenv("postgres://udc9pgcomhsrp8:p9db480dc970a9cbdfffac5b2e765f086f81a19e5c09030c10351ab18df16406e@c3v5n5ajfopshl.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d60vqb4h1327ga")

# 🧩 Postgres bilan bog‘lanish
async def get_db_pool():
    return await asyncpg.create_pool(DATABASE_URL)

# 🔰 Foydalanuvchini bazaga qo‘shish yoki yangilash
async def register_user(pool, user_id, username, invited_by=None):
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT user_id FROM users WHERE user_id = $1", user_id)
        if not user:
            ref_code = str(user_id)
            await conn.execute(
                "INSERT INTO users(user_id, username, ref_code, invited_by) VALUES($1, $2, $3, $4)",
                user_id, username, ref_code, invited_by
            )

# 🧮 Darajani hisoblash
def calculate_level(refs):
    if refs < 10: return "Oddiy"
    elif refs < 15: return "Silver"
    elif refs < 21: return "Gold"
    elif refs < 28: return "Platina 1"
    elif refs < 36: return "Platina 2"
    elif refs < 45: return "Platina 3"
    elif refs < 55: return "Platina 4"
    elif refs < 66: return "Platina 5"
    elif refs < 78: return "Platina 6"
    elif refs < 91: return "Diamond 1"
    elif refs < 105: return "Diamond 2"
    elif refs < 120: return "Diamond 3"
    elif refs < 136: return "Diamond 4"
    elif refs < 153: return "Diamond 5"
    else: return "Diamond 6"

# 📱 Asosiy menyu
def main_menu():
    buttons = [
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="💰 Pul yechish")],
        [KeyboardButton(text="📢 Referal havola")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# 🛠 Database yaratish (agar hali yo‘q bo‘lsa)
async def init_db(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            balance BIGINT DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            level TEXT DEFAULT 'Oddiy',
            ref_code TEXT UNIQUE,
            invited_by BIGINT,
            blocked INTEGER DEFAULT 0
        )
        """)

# 🔰 /start komandasi
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    pool = await get_db_pool()
    await init_db(pool)

    user_id = message.from_user.id
    username = message.from_user.username or "NoName"
    args = message.text.split()
    invited_by = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    await register_user(pool, user_id, username, invited_by)

    if invited_by and invited_by != user_id:
        async with pool.acquire() as conn:
            inviter = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", invited_by)
            if inviter:
                await conn.execute(
                    "UPDATE users SET balance = balance + 5000, referrals = referrals + 1 WHERE user_id = $1",
                    invited_by
                )
                ref_count = inviter['referrals'] + 1
                new_level = calculate_level(ref_count)
                await conn.execute("UPDATE users SET level = $1 WHERE user_id = $2", new_level, invited_by)

    await message.answer(
        f"👋 Salom, <b>{message.from_user.first_name}</b>!\n\n"
        "🎯 <b>TezRef</b> botga xush kelibsiz!\n\n"
        "💸 Referallar orqali pul ishlang va 30 daqiqada yeching!",
        reply_markup=main_menu()
    )

# 📢 Referal havola
@dp.message(F.text.lower().contains("referal"))
async def referral_link(message: types.Message):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"
    await message.answer(
        f"📢 Har bir do‘st taklifi uchun sizga <b>5000 so‘m</b> beriladi!:\n<a href='{link}'>{link}</a>\n\n"
        "Havolani do‘stlaringizga jo‘nating!",
        parse_mode=ParseMode.HTML
    )

# 📊 Statistika
@dp.message(F.text.lower().contains("statistika"))
async def stats_cmd(message: types.Message):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT balance, referrals, level, blocked FROM users WHERE user_id = $1", message.from_user.id
        )
    if user:
        balance, refs, level, blocked = user['balance'], user['referrals'], user['level'], user['blocked']
        status = "🟢 Aktiv" if blocked == 0 else "🔴 Bloklangan"
        await message.answer(
            f"📊 <b>Sizning statistikangiz:</b>\n\n"
            f"👥 Referallar: <b>{refs}</b>\n"
            f"💰 Balans: <b>{balance} so‘m</b>\n"
            f"🏅 Daraja: <b>{level}</b>\n"
            f"⚙️ Holat: {status}"
        )
    else:
        await message.answer("Siz hali ro‘yxatdan o‘tmagansiz.")

# 💸 FSM uchun step-lar
class WithdrawState(StatesGroup):
    card = State()
    amount = State()

# 💸 Pul yechish boshlanishi
@dp.message(F.text.lower().contains("pul"))
async def withdraw_cmd(message: types.Message, state: FSMContext):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT balance, blocked FROM users WHERE user_id = $1", message.from_user.id)

    if not user:
        await message.answer("Siz hali ro‘yxatdan o‘tmagansiz.")
        return
    balance, blocked = user['balance'], user['blocked']
    if blocked == 1:
        await message.answer("🚫 Sizning akkauntingiz bloklangan.")
        return
    if balance < 59000:
        await message.answer("❗ Pul yechish uchun kamida <b>59,000 so‘m</b> kerak.")
        return

    await message.answer("💳 Karta raqamingizni kiriting (masalan: 8600 1234 5678 9999):")
    await state.set_state(WithdrawState.card)

# 💳 Karta raqamini olish
@dp.message(WithdrawState.card)
async def get_card_number(message: types.Message, state: FSMContext):
    card = message.text.strip()
    if not card.replace(" ", "").isdigit() or len(card.replace(" ", "")) not in [16, 20]:
        await message.answer("❌ Noto‘g‘ri karta raqami. Qayta kiriting:")
        return
    await state.update_data(card=card)
    await message.answer("💰 Endi yechmoqchi bo‘lgan summani kiriting (so‘mda):")
    await state.set_state(WithdrawState.amount)

# 💰 Summani olish
@dp.message(WithdrawState.amount)
async def get_withdraw_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    card = data['card']
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Iltimos, faqat raqam kiriting (masalan: 75000).")
        return

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", message.from_user.id)
    balance = user['balance']

    if amount < 59000:
        await message.answer("❗ Minimal yechish summasi — 59,000 so‘m.")
        return
    if amount > balance:
        await message.answer("❌ Hisobingizda buncha mablag‘ yo‘q.")
        return

    buttons = [
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{message.from_user.id}_{amount}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"reject_{message.from_user.id}")
        ]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await bot.send_message(
        ADMIN_ID,
        f"💸 <b>Yangi pul yechish so‘rovi!</b>\n\n"
        f"👤 Foydalanuvchi: @{message.from_user.username}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"💳 Karta: <code>{card}</code>\n"
        f"💰 So‘ralgan summa: <b>{amount} so‘m</b>",
        reply_markup=markup
    )
    await message.answer("✅ So‘rovingiz adminga yuborildi. To‘lov 30 daqiqa ichida amalga oshiriladi.")
    await state.clear()

# ✅ Admin tasdiqlasa
@dp.callback_query(F.data.startswith("approve_"))
async def approve_payout(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    amount = int(parts[2])

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", user_id)
        balance = user['balance']
        if balance >= amount:
            await conn.execute("UPDATE users SET balance = balance - $1 WHERE user_id = $2", amount, user_id)
            await bot.send_message(user_id, f"✅ <b>{amount} so‘m</b> to‘lov amalga oshirildi 💸")
            await callback.message.edit_text(
                f"✅ To‘lov tasdiqlandi!\n\n🆔 ID: <code>{user_id}</code>\n💰 Miqdor: {amount} so‘m"
            )
        else:
            await bot.send_message(user_id, "❌ Hisobingizda yetarli mablag‘ yo‘q.")
            await callback.message.edit_text(
                f"❌ To‘lovni amalga oshib bo‘lmadi. Hisobingizda yetarli mablag‘ yo‘q."
            )

# ❌ Admin bekor qilsa
@dp.callback_query(F.data.startswith("reject_"))
async def reject_payout(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await bot.send_message(user_id, "❌ Sizning pul yechish so‘rovingiz bekor qilindi.")
    await callback.message.edit_text(f"❌ Pul yechish so‘rovi bekor qilindi.\n🆔 ID: <code>{user_id}</code>")

# 🚀 Ishga tushirish
async def main():
    print("🤖 TezRef bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
