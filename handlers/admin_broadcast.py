import asyncio
from aiogram import Router, types, Bot, F
from aiogram.enums import ParseMode
# 🛑 Faqat TelegramAPIError qoldirildi, chunki aniq nom versiya sababli ishlamayapti.
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest 
# TelegramAPIError barcha HTTP 400+ xatolarini o'z ichiga oladi.

from database import get_db_pool
from config import ADMIN_ID 
from handlers.start import main_menu 

admin_broadcast_router = Router()
ADMIN_ID = 496829881 

# --- ADMINLAR UCHUN BUYRUQLAR ---

@admin_broadcast_router.message(F.text.startswith("/broadcast"))
async def start_broadcast(message: types.Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Sizda bu buyruqqa ruxsat yo'q.")
    
    broadcast_message = message.text.removeprefix("/broadcast").strip()
    
    if not broadcast_message:
        return await message.answer("❌ Xabar matnini kiriting! Namuna: /broadcast Bu mening test xabarim.")

    pool = await get_db_pool()
    user_ids = await pool.fetch("SELECT user_id FROM users")
    
    total_users = len(user_ids)
    sent_count = 0
    blocked_count = 0
    error_count = 0
    
    await message.answer(f"Ommaviy xabar yuborish boshlandi. Jami foydalanuvchilar: {total_users}")

    for record in user_ids:
        user_id = record['user_id']
        try:
            await bot.send_message(
                chat_id=user_id,
                text=broadcast_message,
                reply_markup=main_menu() 
            )
            sent_count += 1
            await asyncio.sleep(0.05) 
            
        # 🟢 YECHIM: TelegramAPIError orqali bloklanishni tekshirish
        except TelegramAPIError as e:
            error_message = str(e).lower()
            
            # Bot bloklangan yoki foydalanuvchi deaktivatsiya qilinganini tekshirish (HTTP 403 Forbidden)
            if 'bot was blocked' in error_message or 'user is deactivated' in error_message:
                blocked_count += 1
            elif 'bad request' in error_message:
                # Boshqa Bad Request xatolari (masalan, noto'g'ri user ID, rasm formati va h.k.)
                error_count += 1
            else:
                # Noma'lum API xatolari
                error_count += 1
                
        except Exception as e:
            # Dasturiy xatolar (API ga aloqador bo'lmagan)
            error_count += 1

    report_text = (
        "📢 Ommaviy xabar yuborish yakunlandi:\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {total_users}\n"
        f"✅ <b>Muvaffaqiyatli yuborildi:</b> {sent_count}\n"
        f"❌ <b>Yuborilmadi (Bot bloklangan/Deaktiv):</b> {blocked_count}\n"
        f"⚠️ <b>Yuborilmadi (Boshqa xatolar):</b> {error_count}\n"
        f"📝 <b>Xabar:</b> <i>{broadcast_message}</i>"
    )
    
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=report_text,
        parse_mode=ParseMode.HTML
    )