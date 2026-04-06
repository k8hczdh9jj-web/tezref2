from aiogram import Router, types, F
from aiogram.enums import ParseMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database import get_db_pool 

rating_router = Router()


def rating_menu() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="👥 Do'stlar taklif qilish bo'yicha")],
        [KeyboardButton(text="👥 Guruhga do'st qo'shish bo'yicha")],
        [KeyboardButton(text="⬅️ Ortga")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


async def _users_count(conn) -> int:
    return await conn.fetchval("SELECT COUNT(*) FROM users")


def _display_name(user_id: int, username: str | None) -> str:
    if username:
        return f"@{username}"
    return f"ID:{user_id}"


async def _show_not_ready_text(message: types.Message, title: str, total_users: int):
    await message.answer(
        f"🏆 <b>{title}</b>\n\n"
        "Reyting (TOP 10) tez orada hisoblanadi va ma'lum qilinadi.\n"
        f"Hozircha foydalanuvchilar soni: <b>{total_users}</b>",
        parse_mode=ParseMode.HTML,
    )


@rating_router.message(F.text == "🏆 Reyting")
async def open_rating_menu(message: types.Message):
    await message.answer(
        "🏆 Reyting bo'limi. Yo'nalishni tanlang:",
        reply_markup=rating_menu(),
    )


@rating_router.message(F.text == "👥 Do'stlar taklif qilish bo'yicha")
async def show_referral_ranking(message: types.Message):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        total_users = await _users_count(conn)
        if total_users <= 100:
            await _show_not_ready_text(message, "Do'stlar taklif qilish bo'yicha reyting", total_users)
            return

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

    lines = ["🏆 <b>Do'stlar taklif qilish bo'yicha TOP 10</b>\n"]

    for idx, user in enumerate(top_users, start=1):
        lines.append(
            f"{idx}. {_display_name(user['user_id'], user['username'])} — <b>{user['referrals']}</b> do'st"
        )

    lines.append("")
    if user_rank_row:
        lines.append(f"📈 Sizning o'rningiz: <b>{user_rank_row['pos']}</b>")
        lines.append(f"👥 Siz taklif qilgan do'stlar: <b>{user_rank_row['referrals']}</b>")
    else:
        lines.append("📈 Sizning o'rningiz: <b>yo'q</b>")
        lines.append("👥 Siz taklif qilgan do'stlar: <b>0</b>")

    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)


@rating_router.message(F.text == "👥 Guruhga do'st qo'shish bo'yicha")
async def show_group_ranking(message: types.Message):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        total_users = await _users_count(conn)
        if total_users <= 100:
            await _show_not_ready_text(message, "Guruhga do'st qo'shish bo'yicha reyting", total_users)
            return

        top_users = await conn.fetch("""
            SELECT user_id, username, COALESCE(group_added_count, 0) AS group_added_count
            FROM users
            ORDER BY COALESCE(group_added_count, 0) DESC, user_id ASC
            LIMIT 10
        """)

        user_rank_row = await conn.fetchrow("""
            WITH ranked AS (
                SELECT
                    user_id,
                    COALESCE(group_added_count, 0) AS group_added_count,
                    ROW_NUMBER() OVER (
                        ORDER BY COALESCE(group_added_count, 0) DESC, user_id ASC
                    ) AS pos
                FROM users
            )
            SELECT pos, group_added_count
            FROM ranked
            WHERE user_id = $1
        """, message.from_user.id)

    lines = ["🏆 <b>Guruhga do'st qo'shish bo'yicha TOP 10</b>\n"]

    for idx, user in enumerate(top_users, start=1):
        lines.append(
            f"{idx}. {_display_name(user['user_id'], user['username'])} — "
            f"<b>{user['group_added_count']}</b> odam"
        )

    lines.append("")
    if user_rank_row:
        lines.append(f"📈 Sizning o'rningiz: <b>{user_rank_row['pos']}</b>")
        lines.append(
            f"👥 Siz guruhga qo'shganlar: <b>{user_rank_row['group_added_count']}</b>"
        )
    else:
        lines.append("📈 Sizning o'rningiz: <b>yo'q</b>")
        lines.append("👥 Siz guruhga qo'shganlar: <b>0</b>")

    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
