from aiogram import Router, types, F
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from utils.channel_check import is_member_required_channel
from urllib.parse import quote
from config import ADMIN_ID, REQUIRED_CHANNEL_LINK, WORK_GROUP_NAME, WORK_GROUP_LINK, WORK_GROUP_ID
from database import get_db_pool
from utils.levels import get_level_by_group_adds, get_combined_level

router = Router()


def earning_menu() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="🔗 Referal havola orqali")],
        [KeyboardButton(text="👥 Guruhga do'st qo'shish orqali")],
        [KeyboardButton(text="⬅️ Ortga")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

@router.message(F.text == "💸 Pul ishlash")
async def open_earning_menu(message: types.Message):
    if not await is_member_required_channel(message.bot, message.from_user.id):
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo‘lish", url=REQUIRED_CHANNEL_LINK)],
            [InlineKeyboardButton(text="✅ A’zo bo‘ldim", callback_data="check_subs_earning")],
        ])
        await message.answer(
            "⚠️ Pul ishlash bo'limi uchun avval kanalga a’zo bo‘ling:",
            reply_markup=markup,
        )
        return

    await message.answer(
        "💸 Pul ishlash bo'limi. Kerakli yo'nalishni tanlang:",
        reply_markup=earning_menu(),
    )


@router.message(F.text == "⬅️ Ortga")
async def back_to_main_menu(message: types.Message):
    from .start import main_menu

    await message.answer("Asosiy menyuga qaytdingiz.", reply_markup=main_menu())


@router.message(F.text == "🔗 Referal havola orqali")
async def referral_link(message: types.Message):
    user_id = message.from_user.id

    me = await message.bot.get_me()
    link = f"https://t.me/{me.username}?start={user_id}"

    share_text = (
        "Salom! Men TezRef botda pul ishlayapman.\n\n"
        "✅ Botga kirish uchun quyidagi havolani bosing:\n"
        f"{link}\n\n"
        "🎁 Siz shu havola orqali kirsangiz, menga bonus tushadi."
    )
    share_url = (
        "https://t.me/share/url"
        f"?url={quote(link, safe='')}"
        f"&text={quote(share_text, safe='')}"
    )

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Do'stga yuborish", url=share_url)]
        ]
    )

    await message.answer(
        "💸 <b>Pul ishlash havolangiz tayyor!</b>\n\n"
        f"🔗 <a href='{link}'>Taklif havolasini ochish</a>\n\n"
        "1) Pastdagi <b>Do'stga yuborish</b> tugmasini bosing.\n"
        "2) Xabarni do'stingizga jo'nating.\n"
        "3) Do'stingiz shu havola orqali botga kirsa, sizga bonus tushadi.\n\n"
        "Qancha ko'p do'st taklif qilsangiz, hisobingiz shuncha tez o'sadi.",
        parse_mode=ParseMode.HTML,
        reply_markup=markup,
    )


@router.message(F.text == "👥 Guruhga do'st qo'shish orqali")
async def group_invite_bonus_info(message: types.Message):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT COALESCE(group_added_count, 0) AS group_added_count FROM users WHERE user_id = $1",
            message.from_user.id,
        )

    added_count = user["group_added_count"] if user and user["group_added_count"] is not None else 0
    _, next_bonus = get_level_by_group_adds(added_count + 1)

    group_id_text = f"<code>{WORK_GROUP_ID}</code>" if WORK_GROUP_ID else "hali o'rnatilmagan"
    group_link_text = WORK_GROUP_LINK if WORK_GROUP_LINK else "(link hali berilmagan)"

    buttons = []
    if WORK_GROUP_LINK:
        buttons.append([InlineKeyboardButton(text="👥 Guruhga o'tish", url=WORK_GROUP_LINK)])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

    await message.answer(
        "👥 <b>Guruh orqali bonus</b>\n\n"
        f"Guruh: <b>{WORK_GROUP_NAME}</b>\n"
        f"Guruh ID: {group_id_text}\n"
        f"Guruh havolasi: {group_link_text}\n\n"
        f"✅ Siz guruhga qo'shganlar soni: <b>{added_count}</b>\n"
        f"💰 Keyingi qo'shgan odam uchun taxminiy bonus: <b>{next_bonus} so'm</b>\n\n"
        "Qoidalar:\n"
        "• Faqat siz qo'shgan odamlar hisoblanadi\n"
        "• O'zi link bilan kirganlar hisoblanmaydi\n"
        "• Bir odam faqat bir marta hisoblanadi",
        parse_mode=ParseMode.HTML,
        reply_markup=markup,
    )


@router.message(Command("groupid"))
async def group_id_helper(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    if message.chat.type not in {"group", "supergroup"}:
        await message.answer("Bu komandani guruh ichida yuboring: /groupid")
        return

    await message.answer(
        f"✅ Guruh ID: <code>{message.chat.id}</code>",
        parse_mode=ParseMode.HTML,
    )


@router.message(F.new_chat_members)
async def track_group_added_members(message: types.Message):
    if message.chat.type not in {"group", "supergroup"}:
        return

    if not WORK_GROUP_ID or message.chat.id != WORK_GROUP_ID:
        return

    if not message.from_user or not message.new_chat_members:
        return

    inviter_id = message.from_user.id
    inviter_username = message.from_user.username or f"user{inviter_id}"

    credited_count = 0
    total_bonus = 0

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, username, ref_code)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO NOTHING
            """,
            inviter_id,
            inviter_username,
            str(inviter_id),
        )

        for new_member in message.new_chat_members:
            invited_user_id = new_member.id

            if new_member.is_bot:
                continue

            # User o'zi join qilsa yoki o'zini qo'shsa bonus berilmaydi
            if invited_user_id == inviter_id:
                continue

            current_added = await conn.fetchval(
                "SELECT COALESCE(group_added_count, 0) FROM users WHERE user_id = $1",
                inviter_id,
            )
            _, per_user_bonus = get_level_by_group_adds(current_added + 1)

            current_refs = await conn.fetchval(
                "SELECT COALESCE(referrals, 0) FROM users WHERE user_id = $1",
                inviter_id,
            )

            new_group_count = current_added + 1
            new_level = get_combined_level(current_refs, new_group_count)

            inserted = await conn.fetchval(
                """
                INSERT INTO group_invite_credits (
                    invited_user_id,
                    first_inviter_user_id,
                    group_id,
                    bonus_amount
                )
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (invited_user_id) DO NOTHING
                RETURNING invited_user_id
                """,
                invited_user_id,
                inviter_id,
                message.chat.id,
                per_user_bonus,
            )

            if not inserted:
                continue

            await conn.execute(
                """
                UPDATE users
                SET group_added_count = COALESCE(group_added_count, 0) + 1,
                    balance = balance + $1,
                    level = $2
                WHERE user_id = $3
                """,
                per_user_bonus,
                new_level,
                inviter_id,
            )

            credited_count += 1
            total_bonus += per_user_bonus

    if credited_count > 0:
        try:
            await message.bot.send_message(
                inviter_id,
                f"🎉 Guruhga qo'shganingiz uchun bonus!\n"
                f"👥 Hisoblangan odamlar: <b>{credited_count}</b>\n"
                f"💰 Jami bonus: <b>{total_bonus} so'm</b>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


@router.callback_query(F.data == "check_subs_earning")
async def check_subscription(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if await is_member_required_channel(callback.bot, user_id):
        await callback.message.edit_text("✅ A’zo bo‘lganingiz uchun rahmat!")
        await callback.message.answer(
            "💸 Pul ishlash bo'limi. Kerakli yo'nalishni tanlang:",
            reply_markup=earning_menu(),
        )
    else:
        await callback.answer("❌ Siz hali kanalga a’zo bo‘lmagansiz!", show_alert=True)
