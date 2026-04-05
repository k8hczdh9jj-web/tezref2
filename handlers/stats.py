from aiogram import Router, types, F
from aiogram.enums import ParseMode
from database import get_db_pool

# Routerni stats_router deb nomlang
stats_router = Router()

@stats_router.message(F.text.contains("Statistika"))
async def stats_cmd(message: types.Message):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("""
            SELECT balance, referrals, level, blocked
            FROM users
            WHERE user_id = $1
        """, message.from_user.id)
        
        if not user:
            return await message.answer("Ma'lumot topilmadi.")

        status = "🟢 Aktiv" if user['blocked'] == 0 else "🔴 Bloklangan"

        await message.answer(
            f"📊 <b>Sizning statistikangiz:</b>\n\n"
            f"👥 Do'stlar soni: <b>{user['referrals']}</b>\n"
            f"💰 Xisobingiz: <b>{user['balance']} so‘m</b>\n"
            f"🏅 Daraja: <b>{user['level']}</b>\n"
            f"⚙️ Status: {status}",
            parse_mode=ParseMode.HTML
        )