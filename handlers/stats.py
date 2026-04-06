from aiogram import Router, types, F
from aiogram.enums import ParseMode
from database import get_db_pool
from utils.levels import get_level_progress

# Routerni stats_router deb nomlang
stats_router = Router()

@stats_router.message(F.text.contains("Statistika"))
async def stats_cmd(message: types.Message):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("""
            SELECT balance, referrals, COALESCE(group_added_count, 0) AS group_added_count, level, blocked
            FROM users
            WHERE user_id = $1
        """, message.from_user.id)
        
        if not user:
            return await message.answer("Ma'lumot topilmadi.")

        status = "🟢 Aktiv" if user['blocked'] == 0 else "🔴 Bloklangan"

        await message.answer(
            f"📊 <b>Sizning statistikangiz:</b>\n\n"
            f"👥 Do'stlar soni: <b>{user['referrals']}</b>\n"
            f"👤 Guruhga qo'shganlar: <b>{user['group_added_count']}</b>\n"
            f"💰 Xisobingiz: <b>{user['balance']} so‘m</b>\n"
            f"🏅 Daraja: <b>{user['level']}</b>\n"
            f"⚙️ Status: {status}",
            parse_mode=ParseMode.HTML
        )


@stats_router.message(F.text == "📈 Mening darajam")
async def my_level_cmd(message: types.Message):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            """
            SELECT
                COALESCE(referrals, 0) AS referrals,
                COALESCE(group_added_count, 0) AS group_added_count,
                COALESCE(level, 'Oddiy') AS level
            FROM users
            WHERE user_id = $1
            """,
            message.from_user.id,
        )

        if not user:
            return await message.answer("Ma'lumot topilmadi.")

        refs = int(user["referrals"])
        group_adds = int(user["group_added_count"])
        progress_data = get_level_progress(refs, group_adds)

        current_level = progress_data["current_level"]
        if user["level"] != current_level:
            await conn.execute(
                "UPDATE users SET level = $1 WHERE user_id = $2",
                current_level,
                message.from_user.id,
            )

    progress_value = progress_data["progress"]
    percent = int(round(progress_value * 100))
    remaining_percent = max(0, 100 - percent)
    bar_len = 20
    filled = max(0, min(bar_len, int(round(progress_value * bar_len))))
    bar = ("█" * filled) + ("░" * (bar_len - filled))

    if progress_data["next_level"] is None:
        await message.answer(
            "📈 <b>Mening darajam</b>\n\n"
            f"🏅 Hozirgi darajangiz: <b>{current_level}</b>\n"
            "👑 Siz eng yuqori darajaga chiqqansiz!\n\n"
            f"<code>{bar}</code> <b>{percent}%</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    if progress_data.get("group_locked"):
        requirement_text = (
            f"• 👥 Yana <b>{progress_data['needed_refs']}</b> ta referal\n\n"
            f"🔒 Guruh orqali daraja oshishi vaqtincha yopiq. "
            f"Avval kamida <b>{progress_data['min_refs_for_group_level']}</b> ta referal to'plang.\n\n"
        )
    else:
        requirement_text = (
            f"• 👥 Yana <b>{progress_data['needed_refs']}</b> ta referal\n"
            f"yoki\n"
            f"• 👤 Yana <b>{progress_data['needed_group_adds']}</b> ta odamni guruhga qo'shish\n\n"
        )

    await message.answer(
        "📈 <b>Mening darajam</b>\n\n"
        f"🏅 Hozirgi darajangiz: <b>{current_level}</b>\n"
        f"🎯 Keyingi daraja: <b>{progress_data['next_level']}</b>\n\n"
        "Keyingi darajaga chiqish uchun:\n"
        f"{requirement_text}"
        "⏳ Daraja progressi:\n"
        f"<code>{bar}</code> <b>{percent}%</b>\n"
        f"🔜 Keyingi darajagacha: <b>{remaining_percent}%</b>",
        parse_mode=ParseMode.HTML,
    )