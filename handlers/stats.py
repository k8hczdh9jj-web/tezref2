from aiogram import Router, types, F
from aiogram.enums import ParseMode
from database import get_db_pool

# Routerni stats_router deb nomlang
stats_router = Router()

@stats_router.message(F.text.contains("Statistika"))
async def stats_cmd(message: types.Message):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # User ma'lumotlarini olishda teams jadvalini ham ulaymiz (LEFT JOIN)
        # Agar user jamoada bo'lsa, team_name chiqadi, bo'lmasa NULL bo'ladi
        user = await conn.fetchrow("""
            SELECT u.balance, u.referrals, u.level, u.blocked, t.team_name 
            FROM users u
            LEFT JOIN teams t ON u.team_id = t.team_id
            WHERE u.user_id = $1
        """, message.from_user.id)
        
        if not user:
            return await message.answer("Ma'lumot topilmadi.")

        status = "🟢 Aktiv" if user['blocked'] == 0 else "🔴 Bloklangan"
        
        # Jamoa bor yoki yo'qligini tekshirish
        if user['team_name']:
            team_text = f"<b>{user['team_name']}</b>"
        else:
            team_text = "Jamoaga qo‘shilmagansiz"

        await message.answer(
            f"📊 <b>Sizning statistikangiz:</b>\n\n"
            f"👥 Referallar: <b>{user['referrals']}</b>\n"
            f"💰 Balans: <b>{user['balance']} so‘m</b>\n"
            f"🏅 Daraja: <b>{user['level']}</b>\n"
            f"🛡 Sizning jamoangiz: {team_text}\n"
            f"⚙️ Holat: {status}",
            parse_mode=ParseMode.HTML
        )