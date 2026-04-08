# handlers/start.py
import re
from html import escape
from aiogram import Router, types, F, Bot
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from config import ALERT_CHANNEL_ID
from database import get_db_pool # init_db ni import qilish shart emas
from utils.levels import get_level_by_refs, get_combined_level
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton # main_menu uchun
from utils.phone_gate import phone_request_keyboard

router = Router()

# 📌 Main menu function (startda kerak bo‘ladi)
def main_menu():
    buttons = [
        [KeyboardButton(text="💸 Pul ishlash"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="🗓 Kunlik bonus"), KeyboardButton(text="📈 Mening darajam")],
        [KeyboardButton(text="💰 Pul yechish"), KeyboardButton(text="🎁 Promokod")],
        [KeyboardButton(text="🏆 Reyting")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


async def send_registration_alert(
    bot: Bot,
    user_row,
    first_name: str | None,
    last_name: str | None,
):
    if not ALERT_CHANNEL_ID:
        return

    username = user_row["username"]
    username_text = f"@{escape(username)}" if username else "yo'q"
    full_name = (f"{first_name or ''} {last_name or ''}").strip()
    full_name_text = escape(full_name) if full_name else "yo'q"
    invited_by = user_row["invited_by"]
    invited_by_text = f"<code>{invited_by}</code>" if invited_by else "yo'q"
    created_at = user_row["created_at"]
    created_at_text = created_at.strftime("%d.%m.%Y %H:%M:%S") if created_at else "yo'q"
    phone_text = escape(user_row["phone_number"] or "yo'q")

    alert_text = (
        "🆕 <b>Yangi ro'yxatdan o'tgan foydalanuvchi</b>\n\n"
        f"🆔 ID: <code>{user_row['user_id']}</code>\n"
        f"👤 Ism-familya: <b>{full_name_text}</b>\n"
        f"🔖 Username: <b>{username_text}</b>\n"
        f"📱 Telefon: <code>{phone_text}</code>\n"
        f"👥 Taklif qilgan (invited_by): {invited_by_text}\n"
        f"🔗 Ref kodi: <code>{escape(user_row['ref_code'] or '')}</code>\n"
        f"🏅 Daraja: <b>{escape(user_row['level'] or 'Oddiy')}</b>\n"
        f"👥 Referallar: <b>{int(user_row['referrals'] or 0)}</b>\n"
        f"💰 Balans: <b>{int(user_row['balance'] or 0)} so'm</b>\n"
        f"🕒 Ro'yxatdan o'tgan vaqt: <b>{created_at_text}</b>"
    )

    try:
        await bot.send_message(ALERT_CHANNEL_ID, alert_text, parse_mode=ParseMode.HTML)
    except Exception:
        pass

async def register_user(conn, user_id, username, invited_by=None):
    """Foydalanuvchini bazaga kiritadi va referal bonus ma'lumotini qaytaradi."""
    
    # Ro'yxatdan o'tkazish
    inserted_user_id = await conn.fetchval("""
        INSERT INTO users (user_id, username, ref_code, invited_by, referrals, balance, level, weekly_refs)
        VALUES ($1,$2,$3,$4,0,0,'Oddiy',0)
        ON CONFLICT (user_id) DO NOTHING
        RETURNING user_id
    """, user_id, username, str(user_id), invited_by)

    if not inserted_user_id:
        return None

    # Agar referal orqali kirgan bo‘lsa bonus (faqat yangi qo'shilganlar uchun)
    if invited_by and invited_by != user_id:
        cfg = await conn.fetchrow(
            "SELECT referral_bonus_delta FROM bonus_config WHERE id = 1"
        )
        referral_bonus_delta = int(cfg["referral_bonus_delta"] or 0) if cfg else 0

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
            _, per_ref = get_level_by_refs(total_refs, referral_bonus_delta)
            new_balance = inviter["balance"] + per_ref
            group_added_count = inviter["group_added_count"]
            new_level = get_combined_level(total_refs, group_added_count)

            await conn.execute("""
                UPDATE users
                SET referrals=$1, balance=$2, level=$3
                WHERE user_id=$4
            """, total_refs, new_balance, new_level, invited_by)

            return {
                "inviter_id": invited_by,
                "bonus": per_ref,
                "total_refs": total_refs,
                "new_balance": new_balance,
                "new_level": new_level,
            }

    return None

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
    referral_reward = None

    async with pool.acquire() as conn:
        user_in_db = await conn.fetchrow("SELECT user_id, phone_number FROM users WHERE user_id=$1", user_id)
        
        # Ro'yxatdan o'tish mantiqi: Agar user bazada bo'lmasa, uni yaratamiz
        if not user_in_db:
            referral_reward = await register_user(conn, user_id, username, invited_by)
        else:
            user_phone = user_in_db["phone_number"]

    if referral_reward:
        invited_name = escape(message.from_user.full_name or username)
        try:
            await message.bot.send_message(
                referral_reward["inviter_id"],
                "🎉 <b>Yangi referal qo'shildi!</b>\n\n"
                f"👤 Yangi foydalanuvchi: <b>{invited_name}</b>\n"
                f"💰 Bonus: <b>{referral_reward['bonus']} so'm</b>\n"
                f"👥 Jami referallar: <b>{referral_reward['total_refs']}</b>\n"
                f"📦 Joriy balans: <b>{referral_reward['new_balance']} so'm</b>\n"
                f"🏅 Darajangiz: <b>{referral_reward['new_level']}</b>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

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
    existing_phone = None
    updated_user = None

    async with pool.acquire() as conn:
        existing_phone = await conn.fetchval(
            "SELECT phone_number FROM users WHERE user_id = $1",
            user_id,
        )

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

        updated_user = await conn.fetchrow(
            """
            SELECT
                user_id,
                username,
                phone_number,
                invited_by,
                ref_code,
                level,
                referrals,
                balance,
                created_at
            FROM users
            WHERE user_id = $1
            """,
            user_id,
        )

    if (not existing_phone) and updated_user:
        await send_registration_alert(
            message.bot,
            updated_user,
            message.from_user.first_name,
            message.from_user.last_name,
        )

    await message.answer(
        "✅ Telefon raqamingiz saqlandi. Endi barcha funksiyalardan foydalanishingiz mumkin.",
        reply_markup=main_menu(),
    )