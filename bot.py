from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3
import asyncio

# 🔑 TOKEN VA ADMIN ID
API_TOKEN = "8520385805:AAHjOr3ThLFwjLepdS_9hNupgtwvg-tlALI"
ADMIN_ID = 496829881  # Admin Telegram ID

# 🔧 Bot sozlamalari
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# 🧩 Database funksiyasi
def get_db():
    conn = sqlite3.connect("tezref.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            level TEXT DEFAULT 'Oddiy',
            ref_code TEXT UNIQUE,
            invited_by INTEGER,
            blocked INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn, cursor

# 🔰 Foydalanuvchini bazaga qo‘shish yoki yangilash
def register_user(user_id, username, invited_by=None):
    conn, cursor = get_db()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if user is None:
        ref_code = str(user_id)
        cursor.execute("""
            INSERT INTO users (user_id, username, ref_code, invited_by)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, ref_code, invited_by))
        conn.commit()
    conn.close()

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

# 🔰 /start komandasi
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoName"
    args = message.text.split()
    invited_by = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    register_user(user_id, username, invited_by)

    # Bonus for inviter
    if invited_by and invited_by != user_id:
        conn, cursor = get_db()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (invited_by,))
        inviter = cursor.fetchone()
        if inviter:
            cursor.execute("""
                UPDATE users 
                SET balance = balance + 5000, referrals = referrals + 1 
                WHERE user_id = ?
            """, (invited_by,))
            conn.commit()

            cursor.execute("SELECT referrals FROM users WHERE user_id = ?", (invited_by,))
            ref_count = cursor.fetchone()[0]
            new_level = calculate_level(ref_count)
            cursor.execute("UPDATE users SET level = ? WHERE user_id = ?", (new_level, invited_by))
            conn.commit()
        conn.close()

    await message.answer(
        f"👋 Salom, <b>{message.from_user.first_name}</b>!\n\n"
        "🎯 <b>TezRef</b> botga xush kelibsiz!\n\n"
        "💸 Referallar orqali pul ishlang va 30 daqiqada yeching!",
        reply_markup=main_menu()
    )

# 📢 Referal havola
@dp.message(F.text.lower().contains("referal"))
async def referral_link(message: types.Message):
    user_id = message.from_user.id
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={user_id}"
    await message.answer(
        f"📢 Har bir do‘st taklifi uchun sizga <b>5000 so‘m</b> beriladi!:\n<a href='{link}'>{link}</a>\n\n"
    "Havolani do‘satingizga jo‘nating!",
    parse_mode=ParseMode.HTML
)

# 📊 Statistika
@dp.message(F.text.lower().contains("statistika"))
async def stats_cmd(message: types.Message):
    user_id = message.from_user.id
    conn, cursor = get_db()
    cursor.execute("SELECT balance, referrals, level, blocked FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        balance, refs, level, blocked = user
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
    user_id = message.from_user.id
    conn, cursor = get_db()
    cursor.execute("SELECT balance, blocked FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        await message.answer("Siz hali ro‘yxatdan o‘tmagansiz.")
        return

    balance, blocked = user
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
    user_id = message.from_user.id
    conn, cursor = get_db()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    conn.close()

    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Iltimos, faqat raqam kiriting (masalan: 75000).")
        return

    if amount < 59000:
        await message.answer("❗ Minimal yechish summasi — 59,000 so‘m.")
        return
    if amount > balance:
        await message.answer("❌ Hisobingizda buncha mablag‘ yo‘q.")
        return

    data = await state.get_data()
    card = data["card"]

    buttons = [
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{user_id}_{amount}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"reject_{user_id}")
        ]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await bot.send_message(
        ADMIN_ID,
        f"💸 <b>Yangi pul yechish so‘rovi!</b>\n\n"
        f"👤 Foydalanuvchi: @{message.from_user.username}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
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

    conn, cursor = get_db()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]

    if balance >= amount:
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        await bot.send_message(user_id, f"✅ <b>{amount} so‘m</b> to‘lov amalga oshirildi 💸")
        await callback.message.edit_text(
            f"✅ To‘lov tasdiqlandi!\n\n🆔 ID: <code>{user_id}</code>\n💰 Miqdor: {amount} so‘m"
        )
    else:
        await bot.send_message(user_id, "❌ Hisobingizda yetarli mablag‘ yo‘q.")
        await callback.message.edit_text(
            f"❌ To‘lovni amalga oshib bo‘lmadi. Hisobingizda yetarli mablag‘ yo‘q."
        )
    conn.close()

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
