import asyncio
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError

from config import ADMIN_ID
from database import get_db_pool
from utils.ads_link import AdsLinkManager
from utils.states import AdsState, AdsLinkState   

admin_ads_router = Router()

# ----------------------------
# set_ads_link — admin yangi link
# ----------------------------
@admin_ads_router.message(F.text.startswith("/set_ads_link"))
async def set_ads_link(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Siz admin emassiz.")

    await message.answer("📝 Yangi reklama linkini yuboring:")
    await state.set_state(AdsLinkState.waiting_for_new_link)


@admin_ads_router.message(AdsLinkState.waiting_for_new_link)
async def save_new_ads_link(message: Message, state: FSMContext):
    new_link = message.text.strip()
    pool = await get_db_pool()
    ads_manager = AdsLinkManager(pool)
    await ads_manager.update_link(new_link)

    await message.answer(f"✅ Reklama linki yangilandi:\n{new_link}")
    await state.clear()


# ----------------------------
# broadcast_ads — admin reklama yuboradi
# ----------------------------
@admin_ads_router.message(F.text.startswith("/sendads"))
async def ask_ads_text(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Siz admin emassiz.")

    # Bu yerda faqat matn so‘raladi, hali tarqatmaydi
    await message.answer("📝 Reklama matnini yuboring:")
    await state.set_state(AdsState.waiting_for_ads_text)


@admin_ads_router.message(AdsState.waiting_for_ads_text)
async def send_ads(message: Message, state: FSMContext):
    ads_text = message.text.strip()
    pool = await get_db_pool()
    ads_manager = AdsLinkManager(pool)
    ads_link = (await ads_manager.get_link() or "").strip()

    # ✅ agar link bo'sh bo'lsa yoki noto‘g‘ri formatda bo‘lsa
    if not ads_link:
        await message.answer(
            "❌ Reklama linki hali o‘rnatilmagan yoki noto‘g‘ri.\n"
            " /set_ads_link orqali linkni qo‘ying."
        )
        await state.clear()
        return

    if not ads_link.startswith("http"):
        await message.answer(
            "❌ Reklama linki noto‘g‘ri formatda. Link https:// yoki http:// bilan boshlanishi kerak."
        )
        await state.clear()
        return

    # ✅ InlineKeyboardMarkup yaratish pydantic uchun mos usulda
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Guruhga qo‘shilish", url=ads_link)]
        ]
    )

    
    user_ids = await pool.fetch("SELECT user_id FROM users")

    total_users = len(user_ids)
    sent_count = 0
    blocked_count = 0
    error_count = 0

    await message.answer(
        f"📢 Reklama massoviy yuborilishi boshlandi!\n👥 Jami foydalanuvchilar: {total_users}"
    )

    for record in user_ids:
        user_id = record["user_id"]
        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=ads_text,
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
            sent_count += 1
            await asyncio.sleep(0.05)
        except TelegramAPIError as e:
            err = str(e).lower()
            if "bot was blocked" in err or "user is deactivated" in err:
                blocked_count += 1
            else:
                error_count += 1
        except Exception:
            error_count += 1

    report_text = (
        "📢 <b>Reklama tarqatish yakunlandi:</b>\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {total_users}\n"
        f"✅ <b>Muvaffaqiyatli yuborildi:</b> {sent_count}\n"
        f"❌ <b>Bloklangan/Deaktiv:</b> {blocked_count}\n"
        f"⚠️ <b>Boshqa xatolar:</b> {error_count}\n\n"
        f"📝 <b>Reklama matni:</b> <i>{ads_text}</i>"
    )
    await message.answer(report_text, parse_mode="HTML")
    await state.clear()
