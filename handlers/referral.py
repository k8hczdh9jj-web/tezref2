from aiogram import Router, types, F
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.channel_check import is_member_channel_1

router = Router()

@router.message(F.text == "📢 Referal havola")
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
    await message.answer(
        f"📢 Sizning referal havolangiz:\n\n"
        f"<a href='{link}'>{link}</a>\n\n"
        "Havolani do‘stlaringizga yuboring va pul ishlang!",
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "check_subs_referral")
async def check_subscription(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if await is_member_channel_1(callback.bot, user_id):
        me = await callback.bot.get_me()
        link = f"https://t.me/{me.username}?start={user_id}"
        await callback.message.edit_text(
            f"✅ A’zo bo‘lganingiz uchun rahmat!\n\n"
            f"📢 Sizning referal havolangiz:\n<a href='{link}'>{link}</a>",
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.answer("❌ Siz hali kanalga a’zo bo‘lmagansiz!", show_alert=True)
