from aiogram import Router, types, F
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.channel_check import is_member_channel_1
from urllib.parse import quote

router = Router()

@router.message(F.text == "💸 Pul ishlash")
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
        "Salom! Men TezRef botda pul ishlayapman. "
        "Quyidagi tugma orqali kirsang, ro'yxatdan o'tganingdan keyin menga bonus tushadi 👇"
    )
    share_url = f"https://t.me/share/url?url={quote(link)}&text={quote(share_text)}"

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Do'stga yuborish", url=share_url)]
        ]
    )

    await message.answer(
        "💸 <b>Pul ishlash havolangiz tayyor!</b>\n\n"
        f"🔗 <a href='{link}'>Do'st taklif havolasini ochish</a>\n\n"
        "1) Pastdagi <b>Do'stga yuborish</b> tugmasini bosing.\n"
        "2) Xabarni do'stingizga jo'nating.\n"
        "3) Do'stingiz shu havola orqali botga kirsa, sizga bonus tushadi.\n\n"
        "Qancha ko'p do'st taklif qilsangiz, hisobingiz shuncha tez o'sadi.",
        parse_mode=ParseMode.HTML,
        reply_markup=markup,
    )


@router.callback_query(F.data == "check_subs_referral")
async def check_subscription(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if await is_member_channel_1(callback.bot, user_id):
        me = await callback.bot.get_me()
        link = f"https://t.me/{me.username}?start={user_id}"

        share_text = (
            "Salom! Men TezRef botda pul ishlayapman. "
            "Quyidagi tugma orqali kirsang, ro'yxatdan o'tganingdan keyin menga bonus tushadi 👇"
        )
        share_url = f"https://t.me/share/url?url={quote(link)}&text={quote(share_text)}"

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📤 Do'stga yuborish", url=share_url)]
            ]
        )

        await callback.message.edit_text(
            f"✅ A’zo bo‘lganingiz uchun rahmat!\n\n"
            f"🔗 <a href='{link}'>Do'st taklif havolasini ochish</a>\n\n"
            "Do'stingiz shu havola orqali botga kirsa, sizga bonus tushadi.",
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
        )
    else:
        await callback.answer("❌ Siz hali kanalga a’zo bo‘lmagansiz!", show_alert=True)
