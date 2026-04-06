# handlers/start.py
import re
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from database import get_db_pool # init_db ni import qilish shart emas
from utils.levels import get_level_by_refs, get_combined_level
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton # main_menu uchun
from utils.phone_gate import phone_request_keyboard

router = Router()

# 📌 Main menu function (startda kerak bo‘ladi)
def main_menu():
    buttons = [
        [KeyboardButton(text="💸 Pul ishlash"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="💰 Pul yechish"), KeyboardButton(text="🎁 Promokod")],
        [KeyboardButton(text="🏆 Reyting"), KeyboardButton(text="📈 Mening darajam")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

async def register_user(conn, user_id, username, invited_by=None):
    """Foydalanuvchini bazaga kiritadi va agar referal bo'lsa, bonus beradi."""
    
    # Ro'yxatdan o'tkazish
    await conn.execute("""
        INSERT INTO users (user_id, username, ref_code, invited_by, referrals, balance, level, weekly_refs)
        VALUES ($1,$2,$3,$4,0,0,'Oddiy',0)
        ON CONFLICT (user_id) DO NOTHING
    """, user_id, username, str(user_id), invited_by)

    # Agar referal orqali kirgan bo‘lsa bonus (faqat yangi qo'shilganlar uchun)
    if invited_by and invited_by != user_id:
        inviter = await conn.fetchrow(
            """
            SELECT referrals, balance, COALESCE(group_added_count, 0) AS group_added_count
            FROM users
            WHERE user_id=$1
            """,
            invited_by,
        )
        if inviter:
            # Referal bonus mantiqi
            total_refs = inviter["referrals"] + 1
            _, per_ref = get_level_by_refs(total_refs)
            new_balance = inviter["balance"] + per_ref
            group_added_count = inviter["group_added_count"]
            new_level = get_combined_level(total_refs, group_added_count)

            await conn.execute("""
                UPDATE users
                SET referrals=$1, balance=$2, level=$3
                WHERE user_id=$4
            """, total_refs, new_balance, new_level, invited_by)
            
            # Yangi userning ID sini inviterga qo'shdik.

# ------------------ /start handler ------------------
@router.message(CommandStart())
async def start_cmd(message: types.Message):
    pool = await get_db_pool()
    user_id = message.from_user.id
    username = message.from_user.username or f"user{user_id}"
    
    # 1. 🔹 /start dagi parametrni ajratib olish
    start_param = None
    if len(message.text.split()) > 1:
        start_param = message.text.split()[1]

    # Referal IDni ajratish
    invited_by = None
    if start_param and start_param.isdigit():
        invited_by = int(start_param)

    user_phone = None

    async with pool.acquire() as conn:
        user_in_db = await conn.fetchrow("SELECT user_id, phone_number FROM users WHERE user_id=$1", user_id)
        
        # Ro'yxatdan o'tish mantiqi: Agar user bazada bo'lmasa, uni yaratamiz
        if not user_in_db:
            await register_user(conn, user_id, username, invited_by)
        else:
            user_phone = user_in_db["phone_number"]

    if not user_phone:
        await message.answer(
            "📱 Botdan foydalanishni boshlash uchun telefon raqamingizni ulashing.",
            reply_markup=phone_request_keyboard(),
        )
        return
            
    # 2. 📝 Standart xabar yuborish
    await message.answer(
        f"👋 Salom, <b>{message.from_user.first_name}</b>!\n"
        "💸 TezRef botga xush kelibsiz!\n"
        "Pul ishlashni boshlash uchun menyudan foydalaning.",
        reply_markup=main_menu(),
        parse_mode=ParseMode.HTML
    )


@router.message(F.contact)
async def save_phone_contact(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user{user_id}"

    if not message.contact:
        await message.answer(
            "❌ Telefon raqamini to'g'ri yuboring.",
            reply_markup=phone_request_keyboard(),
        )
        return

    if message.contact.user_id and message.contact.user_id != user_id:
        await message.answer(
            "❌ Faqat o'zingizga tegishli telefon raqamni yuboring.",
            reply_markup=phone_request_keyboard(),
        )
        return

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, username, ref_code)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id,
            username,
            str(user_id),
        )

        await conn.execute(
            """
            UPDATE users
            SET phone_number = $1, username = $2
            WHERE user_id = $3
            """,
            message.contact.phone_number,
            username,
            user_id,
        )

    await message.answer(
        "✅ Telefon raqamingiz saqlandi. Endi barcha funksiyalardan foydalanishingiz mumkin.",
        reply_markup=main_menu(),
    )