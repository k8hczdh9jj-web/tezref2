from aiogram import Router, types, F
from aiogram.enums import ParseMode
from database import get_db_pool 

rating_router = Router()

# Fake TOP 10 foydalanuvchilar
TOP10_MANUAL = [
    3000000,
    2000000,
    1000000,
    500000,
    500000,
    500000,
    300000,
    300000,
    300000,
    300000
]

@rating_router.message(F.text == "🏆 Reyting")
async def show_ranking(message: types.Message):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # haqiqiy foydalanuvchilarni referrals bo'yicha kamayish tartibida olamiz
        users = await conn.fetch("""
            SELECT user_id, username, referrals
            FROM users
            ORDER BY referrals DESC
        """)

    # Faqat qo'lda kiritilgan TOP-10 ro'yxatini ko'rsatamiz
    lines = ["🏆 <b>Haftalik Reyting (TOP 10)</b>\n"]
    for i, prize in enumerate(TOP10_MANUAL, start=1):
        lines.append(f"{i} - o‘rin: <b>{prize:,}</b> so‘m 💰")

    # Foydalanuvchining o'rnini aniqlaymiz (haqiqiy foydalanuvchilar 11-o'rindan boshlanadi)
    user_rank = None
    user_refs = 0
    for idx, u in enumerate(users, start=11):
        if u["user_id"] == message.from_user.id:
            user_rank = idx
            user_refs = u["referrals"]
            break

    # Qo'shimcha xabar: foydalanuvchiga o'z o'rni yoki yo'qligi haqida ma'lumot
    lines.append("")  # bo'sh qator
    if user_rank:
        lines.append(f"📈 Siz hozirda <b>{user_rank}-o‘rindasiz</b>!")
        lines.append(f"👥 Sizda jami <b>{user_refs}</b> ta referal bor.")
    else:
        # agar foydalanuvchi users listida bo'lmasa — u hali referal chaqirmagan yoki 0 refs
        # bazadan uning o'z referal sonini olish (agar user mavjud bo'lsa)
        async with pool.acquire() as conn:
            own = await conn.fetchrow("SELECT referrals FROM users WHERE user_id = $1", message.from_user.id)
        own_refs = own['referrals'] if own else 0
        lines.append("❗ Siz TOP-10 ga kirmagansiz.")
        lines.append(f"👥 Sizda jami <b>{own_refs}</b> ta referal bor. Ko‘proq do‘stlaringizni taklif qiling!")

    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
