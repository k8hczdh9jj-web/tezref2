from aiogram import Router, types, F
from aiogram.enums import ParseMode
from database import get_db_pool 

rating_router = Router()

@rating_router.message(F.text == "🏆 Reyting")
async def show_ranking(message: types.Message):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        top_users = await conn.fetch("""
            SELECT user_id, username, referrals
            FROM users
            ORDER BY referrals DESC, user_id ASC
            LIMIT 10
        """)

        user_rank_row = await conn.fetchrow("""
            WITH ranked AS (
                SELECT
                    user_id,
                    referrals,
                    ROW_NUMBER() OVER (ORDER BY referrals DESC, user_id ASC) AS pos
                FROM users
            )
            SELECT pos, referrals
            FROM ranked
            WHERE user_id = $1
        """, message.from_user.id)

    lines = ["🏆 <b>Reyting (TOP 10)</b>\n"]

    if not top_users:
        lines.append("Hozircha reyting uchun ma'lumotlar yo'q.")
    else:
        for idx, user in enumerate(top_users, start=1):
            name = user["username"]
            if name:
                display_name = f"@{name}"
            else:
                display_name = f"ID:{user['user_id']}"

            lines.append(
                f"{idx}. {display_name} — <b>{user['referrals']}</b> do'st"
            )

    lines.append("")
    if user_rank_row:
        lines.append(f"📈 Sizning o'rningiz: <b>{user_rank_row['pos']}</b>")
        lines.append(f"👥 Siz taklif qilgan do'stlar: <b>{user_rank_row['referrals']}</b>")
    else:
        lines.append("📈 Sizning o'rningiz: <b>yo'q</b>")
        lines.append("👥 Siz taklif qilgan do'stlar: <b>0</b>")

    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
