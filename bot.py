# Full updated bot with channel join check (aiogram 3.20+)
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
import asyncio
import os
import asyncpg
import ssl

# ------------------ CONFIG ------------------
API_TOKEN = "8401942831:AAF7rQa6UC7YGNyIk9gdx1XnaiyxZlt5lJA"
ADMIN_ID = 496829881
ADMIN_USERNAME = "tezref_admin1"
CHANNEL_USERNAME = "@tezrefofficial"
CHANNEL_USERNAME_2 = '@tezrefpromo'
DATABASE_URL = os.getenv("DATABASE_URL")

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# ------------------ BOT INIT ------------------
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ------------------ DB SETUP ------------------
db_pool = None
async def get_db_pool():
    global db_pool
    if db_pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set.")
        db_pool = await asyncpg.create_pool(DATABASE_URL, ssl=ssl_context)
    return db_pool

async def init_db(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                balance BIGINT DEFAULT 0,
                referrals INTEGER DEFAULT 0,
                weekly_refs INTEGER DEFAULT 0,
                level TEXT DEFAULT 'Oddiy',
                ref_code TEXT UNIQUE,
                invited_by BIGINT,
                blocked INTEGER DEFAULT 0
            )
        """)
        # --- PROMOKOD JADVALLARI ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                amount BIGINT NOT NULL,
                max_uses INT NOT NULL,
                uses_left INT NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                channel_id BIGINT DEFAULT NULL,
                created_by BIGINT,
                created_at TIMESTAMP DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS promo_claims (
                code TEXT REFERENCES promo_codes(code),
                user_id BIGINT,
                claimed_at TIMESTAMP DEFAULT now(),
                PRIMARY KEY (code, user_id)
            )
        """)

# ------------------ level ------------------
level = [
    ("Oddiy", 3, 1500),
    ("Bronza", 10, 1750),
    ("Silver", 50, 2250),
    ("Gold", 200, 2500),
    ("Platina 1", 300, 3000),
    ("Platina 2", 450, 3000),
    ("Platina 3", 600, 3500),
    ("Platina 4", 800, 4000),
    ("Platina 5", 1200, 5000),
    ("Platina 6", 1800, 6000),
    ("Diamond 1", 2500, 7000),
    ("Diamond 2", 3200, 8000),
    ("Diamond 3", 4000, 2250),
    ("Diamond 4", 5000, 2250),
    ("Diamond 5", 6000, 2250),
    ("Diamond 6", float('inf'), 2250),
]
# 🔹 BAZADAGI FOYDALANUVCHI LEVELINI REFERAL SONIGA QARAB YANGILASH
async def update_levels_by_referrals(pool):
    async with pool.acquire() as conn:
        users = await conn.fetch("SELECT user_id, referrals FROM users")
        for user in users:
            user_id = user['user_id']
            refs = user['referrals']
            new_level, _ = get_level_by_refs(refs)
            await conn.execute(
                "UPDATE users SET level=$1 WHERE user_id=$2",
                new_level, user_id
            )

def get_level_by_refs(refs: int):
    for name, upper, per_ref in level:
        if refs < upper:
            return name, per_ref
    return level[-1][0], level[-1][2]

def get_total_earned_until_refs(refs: int):
    total, prev = 0, 0
    for name, upper, per_ref in level:
        if upper == float('inf'):
            total += max(0, refs - prev) * per_ref
            break
        else:
            total += max(0, min(refs, upper) - prev) * per_ref
            prev = upper
    return total

# ------------------ MAIN MENU ------------------
def main_menu():
    buttons = [
        [KeyboardButton(text="📢 Referal havola"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="💰 Pul yechish"), KeyboardButton(text="🏆 Reyting")],
        [KeyboardButton(text="🎁 Promokod"), KeyboardButton(text="📞 Adminga murojaat")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ------------------ /start ------------------
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    pool = await get_db_pool()
    await init_db(pool)

    user_id = message.from_user.id
    username = message.from_user.username or f"user{user_id}"

    # /start dan keyingi argumentni olish (taklifchi)
    invited_by = None
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1 and parts[1].isdigit():
            invited_by = int(parts[1])

    async with pool.acquire() as conn:
        # Foydalanuvchi bazada bormi?
        user = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)

        # 🔹 Yangi foydalanuvchini qo‘shish
        if not user:
            await conn.execute(
                """
                INSERT INTO users (user_id, username, ref_code, invited_by, referrals, balance, level, weekly_refs)
                VALUES ($1,$2,$3,$4,0,0,'Oddiy',0)
                """,
                user_id, username, str(user_id), invited_by
)

            # 🔹 Agar referal orqali kirgan bo‘lsa — bonus berish
            if invited_by and invited_by != user_id:
                inviter = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", invited_by)
                if inviter:
                    # jami referallar soni bazadagi eski son +1
                    total_refs = inviter["referrals"] + 1
                    new_level, per_ref = get_level_by_refs(total_refs)
                    new_balance = inviter["balance"] + per_ref

                    await conn.execute("""
                       UPDATE users
                       SET referrals=$1,
                           balance=$2,
                           level=$3
                       WHERE user_id=$4
                    """, total_refs, new_balance, new_level, invited_by)


    # Foydalanuvchining yangi referral bilan statistikasi
    async with pool.acquire() as conn:
        updated_user = await conn.fetchrow("SELECT referrals FROM users WHERE user_id=$1", user_id)

    await message.answer(
        f"👋 Salom, <b>{message.from_user.first_name}</b>!\n"
        "💸 TezRef botga xush kelibsiz!\n"
        "Pul ishlashni boshlash uchun menyudan foydalaning.",
        reply_markup=main_menu()
    )

# ------------------ CHANNEL CHECK ------------------
async def is_member(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME.replace('@',''), user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        print(f"❌ get_chat_member error: {e}")
        return False

# ------------------ HANDLERS ------------------
# Referal havola - majburiy kanal
@dp.message(F.text == "📢 Referal havola")
async def referral_link(message: types.Message):
    user_id = message.from_user.id
    if not await is_member(user_id):
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
            [InlineKeyboardButton(text="✅ A’zo bo‘ldim", callback_data="check_subs")]
        ])
        return await message.answer("⚠️ Iltimos, botdan foydalanish uchun kanalga a’zo bo‘ling:", reply_markup=markup)

    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={user_id}"
    await message.answer(f"📢 Sizning referal havolangiz:\n\n<a href='{link}'>{link}</a>\n\n"
                         "Havolani do'stlaringizga yuboring va pul ishlang!", parse_mode=ParseMode.HTML)

@dp.callback_query(F.data == "check_subs")
async def check_subscription(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    for _ in range(5):
        try:
            member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
            if member.status in ['creator', 'administrator', 'member']:
                me = await bot.get_me()
                link = f"https://t.me/{me.username}?start={user_id}"
                await callback.message.edit_text(
                    f"✅ A’zo bo‘lganingiz uchun rahmat!\n\n"
                    f"📢 Sizning referal havolangiz:\n<a href='{link}'>{link}</a>",
                    parse_mode=ParseMode.HTML
                )
                return
        except Exception as e:
            print(f"❌ get_chat_member error: {e}")
        await asyncio.sleep(2)
    await callback.answer("❌ Siz hali kanalga a’zo bo‘lmagansiz!", show_alert=True)

# ------------------ PROMOKOD FSM ------------------
class PromoState(StatesGroup):
    waiting_for_code = State()


# ------------------ PROMOKOD MENYU ------------------
@dp.message(F.text.lower() == "🎁 promokod")
async def show_promocode_menu(message: types.Message):
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Promokodni olish", url=f"https://t.me/{CHANNEL_USERNAME_2.replace('@','')}")],
        [InlineKeyboardButton(text="✏️ Promokodni terish", callback_data="enter_promo")]
    ])
    await message.answer("🎁 Promokod bo‘limi:", reply_markup=buttons)


# ------------------ PROMOKOD TERISH HANDLER ------------------
@dp.callback_query(lambda c: c.data == "enter_promo")
async def enter_promo(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME_2, user_id)
        if member.status in ['left', 'kicked']:
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME_2.replace('@','')}")]
            ])
            # Eski xabarni yangilaymiz: matn va tugmalar
            await callback.message.edit_text(
                "⚠️ Promokodni kiritish uchun kanalga a’zo bo‘ling:",
                reply_markup=markup
            )
            return
    except:
        await callback.message.edit_text(
            "⚠️ Kanalga a'zoligingizni tekshirib bo‘lmadi.",
            reply_markup=None
        )
        return

    # Agar kanalga a'zo bo'lsa, eski xabarni butunlay yangilaymiz
    await callback.message.edit_text(
        "✏️ Iltimos, kanaldan olgan promokodingizni kiriting:",
        reply_markup=None
    )
    await state.set_state(PromoState.waiting_for_code)


# ------------------ PROMOKOD CLAIM FSM ------------------
@dp.message(PromoState.waiting_for_code)
async def claim_promo_fsm(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    user_id = message.from_user.id

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        promo = await conn.fetchrow("SELECT * FROM promo_codes WHERE code=$1 AND active=TRUE", code)
        if not promo:
            await state.clear() 
            return await message.answer("❌ Bunday aktiv promokod topilmadi.")

        async with conn.transaction():
            already = await conn.fetchval("SELECT 1 FROM promo_claims WHERE code=$1 AND user_id=$2", code, user_id)
            if already:
                await state.clear() 
                return await message.answer("❌ Siz ushbu promokodni allaqachon ishlatgansiz.")

            row = await conn.fetchrow("""
                UPDATE promo_codes SET uses_left = uses_left - 1
                WHERE code=$1 AND uses_left > 0
                RETURNING amount, uses_left
            """, code)
            if not row:
                await state.clear() 
                return await message.answer("❌ Afsuski, promokod tugab qolgan.")

            await conn.execute("INSERT INTO promo_claims(code, user_id) VALUES($1,$2)", code, user_id)
            await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", row['amount'], user_id)

    await message.answer(f"🎉 Tabriklaymiz! Sizga {row['amount']} so'm qo‘shildi!")
    await state.clear()

# Admin create promo
@dp.message(F.text.startswith("/createpromo"))
async def create_promo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Bu buyruq faqat adminlarga.")
    
    parts = message.text.split()
    if len(parts) < 4:
        return await message.answer("Foydalanish: /createpromo CODE AMOUNT MAX_USES")
    
    code = parts[1].upper()
    try:
        amount = int(parts[2])
        max_uses = int(parts[3])
    except ValueError:
        return await message.answer("❌ Amount va MAX_USES son bo‘lishi kerak.")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute("""
                INSERT INTO promo_codes(code, amount, max_uses, uses_left, created_by)
                VALUES($1, $2, $3, $3, $4)
            """, code, amount, max_uses, message.from_user.id)
        except asyncpg.UniqueViolationError:
            return await message.answer("❌ Bunday kod mavjud.")
    
    await message.answer(f"✅ Promokod {code} yaratildi: {amount} so'm, {max_uses} ta ishlash mumkin.")

# Statistika
@dp.message(F.text.contains("Statistika"))
async def stats_cmd(message: types.Message):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # real vaqtda referallarni hisoblash
        total_refs = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE invited_by=$1", message.from_user.id
        )
        user = await conn.fetchrow(
            "SELECT balance, referrals, level, blocked FROM users WHERE user_id=$1", 
            message.from_user.id
        )
        status = "🟢 Aktiv" if user['blocked'] == 0 else "🔴 Bloklangan"

        await message.answer(
            f"📊 <b>Sizning statistikangiz:</b>\n\n"
            f"👥 Referallar: <b>{user['referrals']}</b>\n"
            f"💰 Balans: <b>{user['balance']} so‘m</b>\n"
            f"🏅 Daraja: <b>{user['level']}</b>\n"
            f"⚙️ Holat: {status}"
        )

# 💸 FSM — pul yechish
class WithdrawState(StatesGroup):
    card = State()
    amount = State()

MIN_WITHDRAW = 60000
MAX_WITHDRAW = 100000

@dp.message(F.text == "💰 Pul yechish")
async def withdraw_cmd(message: types.Message, state: FSMContext):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT balance, blocked FROM users WHERE user_id = $1", message.from_user.id)

    if not user:
        return await message.answer("Siz hali ro‘yxatdan o‘tmagansiz.")
    if user['blocked'] == 1:
        return await message.answer("🚫 Sizning akkauntingiz bloklangan.")
    if user['balance'] < MIN_WITHDRAW:
        return await message.answer(f"❗ Pul yechish uchun kamida <b>{MIN_WITHDRAW:,} so‘m</b> kerak.")

    await message.answer("💳 Karta raqamingizni kiriting (masalan: 8600 1234 5678 9999):")
    await state.set_state(WithdrawState.card)

@dp.message(WithdrawState.card)
async def get_card_number(message: types.Message, state: FSMContext):
    card = message.text.strip()
    if not card.replace(" ", "").isdigit() or len(card.replace(" ", "")) not in [16, 20]:
        return await message.answer("❌ Noto‘g‘ri karta raqami. Qayta kiriting:")
    await state.update_data(card=card)
    await message.answer(f"💰 Endi yechmoqchi bo‘lgan summani kiriting:")
    await state.set_state(WithdrawState.amount)

@dp.message(WithdrawState.amount)
async def get_withdraw_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    card = data['card']
    try:
        amount = int(message.text.strip())
    except ValueError:
        return await message.answer("❌ Faqat raqam kiriting (masalan: 7500).")

    if amount < MIN_WITHDRAW:
        return await message.answer(f"❗ Minimal yechish summasi — {MIN_WITHDRAW:,} so‘m.")
    if amount > MAX_WITHDRAW:
        return await message.answer(f"❗ Maksimal yechish summasi — {MAX_WITHDRAW:,} so‘m.")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", message.from_user.id)
    balance = user['balance']

    if amount > balance:
        return await message.answer("❌ Hisobingizda yetarli mablag‘ yo‘q.")

    markup = InlineKeyboardMarkup(inline_keyboard=[[ 
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{message.from_user.id}_{amount}"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"reject_{message.from_user.id}")
    ]])
    username = f"@{message.from_user.username}" if message.from_user.username else f"ID:{message.from_user.id}"
    await bot.send_message(
        ADMIN_ID,
        f"💸 <b>Yangi pul yechish so‘rovi!</b>\n\n"
         f"👤 Foydalanuvchi: {username}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"💳 Karta: <code>{card}</code>\n"
        f"💰 So‘ralgan summa: <b>{amount} so‘m</b>",
        reply_markup=markup
    )
    await message.answer("✅ So‘rovingiz adminga yuborildi. To‘lov 24 soat ichida amalga oshiriladi.")
    await state.clear()

@dp.callback_query(F.data.startswith("approve_"))
async def approve_payout(callback: types.CallbackQuery):
    _, user_id, amount = callback.data.split("_")
    user_id, amount = int(user_id), int(amount)
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():  # ✅ transaction qo‘shildi
            # foydalanuvchini bazadan olish
            user = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", user_id)
            if not user:
                await callback.answer("❌ Foydalanuvchi topilmadi", show_alert=True)
                return

            if user['balance'] < amount:
                await bot.send_message(user_id, "❌ Hisobingizda yetarli mablag‘ yo‘q.")
                await callback.message.edit_text(
                    "❌ To‘lov amalga oshmadi — balans yetarli emas.",
                    reply_markup=None
                )
                return

            # 1️⃣ Balansdan pul yechish
            await conn.execute("UPDATE users SET balance = balance - $1 WHERE user_id = $2", amount, user_id)

            # 2️⃣ Foydalanuvchiga xabar yuborish
            await bot.send_message(user_id, f"✅ <b>{amount} so‘m</b> to‘lov amalga oshirildi 💸")

            # 3️⃣ Foydalanuvchi statistikasi: referal va levelni yangilash
            total_refs = await conn.fetchval("SELECT COUNT(*) FROM users WHERE invited_by=$1", user_id)
            new_level, _ = get_level_by_refs(total_refs)
            await conn.execute(
                "UPDATE users SET level=$1, referrals=$2 WHERE user_id=$3",
                new_level, total_refs, user_id
            )

            # 4️⃣ Admin xabarini yangilash va tugmalarni olib tashlash
            await callback.message.edit_text(
                f"✅ To‘lov tasdiqlandi!\n🆔 ID: {user_id}\n💰 {amount} so‘m",
                reply_markup=None
            )

@dp.callback_query(F.data.startswith("reject_"))
async def reject_payout(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await bot.send_message(user_id, "❌ Sizning pul yechish so‘rovingiz bekor qilindi.")
    await callback.message.edit_text(
        f"❌ Pul yechish so‘rovi bekor qilindi.\n🆔 ID: {user_id}",
        reply_markup=None
    )

# Fake TOP 10 foydalanuvchilar
TOP10_MANUAL = [
    3000000,
    2000000,
    1000000,
    500000,
    500000,
    500000,
    300000,
    300000,
    300000,
    300000
]
# Reyting
@dp.message(F.text.lower().contains("reyting"))
async def show_ranking(message: types.Message):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # haqiqiy foydalanuvchilarni referrals bo'yicha kamayish tartibida olamiz
        users = await conn.fetch("""
            SELECT user_id, username, referrals
            FROM users
            ORDER BY referrals DESC
        """)

    # Faqat qo'lda kiritilgan TOP-10 ro'yxatini ko'rsatamiz
    lines = ["🏆 <b>Haftalik Reyting (TOP 10)</b>\n"]
    for i, prize in enumerate(TOP10_MANUAL, start=1):
        lines.append(f"{i} - o‘rin: <b>{prize:,}</b> so‘m 💰")

    # Foydalanuvchining o'rnini aniqlaymiz (haqiqiy foydalanuvchilar 11-o'rindan boshlanadi)
    user_rank = None
    user_refs = 0
    for idx, u in enumerate(users, start=11):
        if u["user_id"] == message.from_user.id:
            user_rank = idx
            user_refs = u["referrals"]
            break

    # Qo'shimcha xabar: foydalanuvchiga o'z o'rni yoki yo'qligi haqida ma'lumot
    lines.append("")  # bo'sh qator
    if user_rank:
        lines.append(f"📈 Siz hozirda <b>{user_rank}-o‘rindasiz</b>!")
        lines.append(f"👥 Sizda jami <b>{user_refs}</b> ta referal bor.")
    else:
        # agar foydalanuvchi users listida bo'lmasa — u hali referal chaqirmagan yoki 0 refs
        # bazadan uning o'z referal sonini olish (agar user mavjud bo'lsa)
        async with pool.acquire() as conn:
            own = await conn.fetchrow("SELECT referrals FROM users WHERE user_id = $1", message.from_user.id)
        own_refs = own['referrals'] if own else 0
        lines.append("❗ Siz TOP-10 ga kirmagansiz.")
        lines.append(f"👥 Sizda jami <b>{own_refs}</b> ta referal bor. Ko‘proq do‘stlaringizni taklif qiling!")

    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)

# Adminga murojaat
@dp.message(F.text.contains("Adminga murojaat"))
async def contact_admin(message: types.Message):
    await message.answer(f"📞 Admin bilan bog‘laning: @{ADMIN_USERNAME}")



# ------------------ RUN ------------------
async def main():
    print("🤖 TezRef bot ishga tushdi...")
    pool = await get_db_pool()
    await init_db(pool)
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())
