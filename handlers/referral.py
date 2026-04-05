from aiogram import Router, types, F
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from utils.channel_check import is_member_channel_1
from urllib.parse import quote
from config import ADMIN_ID, WORK_GROUP_NAME, WORK_GROUP_LINK, WORK_GROUP_ID

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

    # Kanalga a’zo ekanligini tekshirish
    if not await is_member_channel_1(message.bot, user_id):
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo‘lish", url=f"https://t.me/tezrefofficial")],
            [InlineKeyboardButton(text="✅ A’zo bo‘ldim", callback_data="check_subs_referral")]
        ])
        return await message.answer("⚠️ Botdan foydalanish uchun kanalga a’zo bo‘ling:", reply_markup=markup)

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
    group_id_text = f"<code>{WORK_GROUP_ID}</code>" if WORK_GROUP_ID else "hali o'rnatilmagan"
    group_link_text = WORK_GROUP_LINK if WORK_GROUP_LINK else "(link hali berilmagan)"

    await message.answer(
        "👥 <b>Guruh orqali bonus</b>\n\n"
        f"Guruh: <b>{WORK_GROUP_NAME}</b>\n"
        f"Guruh ID: {group_id_text}\n"
        f"Guruh havolasi: {group_link_text}\n\n"
        "Yaqin bosqichda bonuslarni shu bo'limga ulaymiz.",
        parse_mode=ParseMode.HTML,
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


@router.callback_query(F.data == "check_subs_referral")
async def check_subscription(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if await is_member_channel_1(callback.bot, user_id):
        me = await callback.bot.get_me()
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

        await callback.message.edit_text(
            f"✅ A’zo bo‘lganingiz uchun rahmat!\n\n"
            f"🔗 <a href='{link}'>Taklif havolasini ochish</a>\n\n"
            "Do'stingiz shu havola orqali botga kirsa, sizga bonus tushadi.",
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
        )
    else:
        await callback.answer("❌ Siz hali kanalga a’zo bo‘lmagansiz!", show_alert=True)
