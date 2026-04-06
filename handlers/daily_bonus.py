from datetime import date, timedelta

from aiogram import F, Router, types
from aiogram.enums import ParseMode

from database import get_db_pool

router = Router()

DAILY_BONUS_AMOUNT = 500
DAILY_BONUS_DAYS = 30


def _render_bonus_calendar(start_date: date, today: date, claimed_dates: set[date]) -> str:
    cells = []
    for idx in range(DAILY_BONUS_DAYS):
        day_date = start_date + timedelta(days=idx)
        label = f"{idx + 1:02d}"

        if day_date in claimed_dates:
            icon = "✅"
        elif day_date < today:
            icon = "❌"
        elif day_date == today:
            icon = "🎁"
        else:
            icon = "▫️"

        cells.append(f"{icon}{label}")

    rows = []
    row_size = 5
    for i in range(0, len(cells), row_size):
        rows.append(" ".join(cells[i:i + row_size]))
    return "\n".join(rows)


def _window_dates(start_date: date) -> tuple[date, date]:
    end_date = start_date + timedelta(days=DAILY_BONUS_DAYS - 1)
    return start_date, end_date


@router.message(F.text == "🗓 Kunlik bonus")
async def claim_daily_bonus(message: types.Message):
    user_id = message.from_user.id
    today = date.today()

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            """
            SELECT created_at, balance
            FROM users
            WHERE user_id = $1
            """,
            user_id,
        )

        if not user:
            await message.answer("Avval /start bosib ro'yxatdan o'ting.")
            return

        start_date = user["created_at"].date()
        _, end_date = _window_dates(start_date)

        claims = await conn.fetch(
            """
            SELECT claim_date, streak_day
            FROM daily_bonus_claims
            WHERE user_id = $1
            ORDER BY claim_date ASC
            """,
            user_id,
        )
        claimed_dates = {row["claim_date"] for row in claims}
        last_claim = claims[-1] if claims else None

        if today > end_date:
            calendar = _render_bonus_calendar(start_date, today, claimed_dates)
            await message.answer(
                "🎁 <b>Kunlik bonus davri yakunlandi.</b>\n\n"
                f"Siz 30 kunlik oynani tugatdingiz.\n"
                f"📅 Boshlangan sana: <b>{start_date.strftime('%d.%m.%Y')}</b>\n"
                f"✅ Olingan bonus kunlari: <b>{len(claimed_dates)}</b>\n\n"
                f"<code>{calendar}</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        if today in claimed_dates:
            streak_day = last_claim["streak_day"] if last_claim else 1
            program_day = (today - start_date).days + 1
            calendar = _render_bonus_calendar(start_date, today, claimed_dates)
            await message.answer(
                "✅ <b>Bugungi kunlik bonus allaqachon olingan.</b>\n\n"
                f"📅 Dastur kuni: <b>{program_day}/{DAILY_BONUS_DAYS}</b>\n"
                f"🔥 Ketma-ket bonus kuni: <b>{streak_day}</b>\n"
                f"💰 Kunlik mukofot: <b>{DAILY_BONUS_AMOUNT} so'm</b>\n\n"
                f"<code>{calendar}</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        restart_text = ""
        if last_claim and last_claim["claim_date"] == today - timedelta(days=1):
            streak_day = min(last_claim["streak_day"] + 1, DAILY_BONUS_DAYS)
        else:
            streak_day = 1
            if last_claim and last_claim["claim_date"] < today - timedelta(days=1):
                restart_text = "🔄 Bir kun o'tkazib yuborilganligi sabab ketma-ket hisob qayta <b>1-kun</b>dan boshlandi.\n\n"

        inserted = False
        async with conn.transaction():
            inserted = await conn.fetchval(
                """
                INSERT INTO daily_bonus_claims (user_id, claim_date, amount, streak_day)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, claim_date) DO NOTHING
                RETURNING 1
                """,
                user_id,
                today,
                DAILY_BONUS_AMOUNT,
                streak_day,
            )

            if inserted:
                await conn.execute(
                    "UPDATE users SET balance = balance + $1 WHERE user_id = $2",
                    DAILY_BONUS_AMOUNT,
                    user_id,
                )

            new_balance = await conn.fetchval(
                "SELECT balance FROM users WHERE user_id = $1",
                user_id,
            )

        if not inserted:
            claimed_dates.add(today)
            program_day = (today - start_date).days + 1
            calendar = _render_bonus_calendar(start_date, today, claimed_dates)
            await message.answer(
                "✅ <b>Bugungi kunlik bonus allaqachon olingan.</b>\n\n"
                f"📅 Dastur kuni: <b>{program_day}/{DAILY_BONUS_DAYS}</b>\n"
                f"🔥 Ketma-ket bonus kuni: <b>{streak_day}</b>\n"
                f"💰 Kunlik mukofot: <b>{DAILY_BONUS_AMOUNT} so'm</b>\n\n"
                f"<code>{calendar}</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        claimed_dates.add(today)
        program_day = (today - start_date).days + 1
        days_left = (end_date - today).days
        calendar = _render_bonus_calendar(start_date, today, claimed_dates)

    await message.answer(
        "🎉 <b>Tabriklaymiz! Kunlik bonus olindi.</b>\n\n"
        f"{restart_text}"
        f"💰 Bonus: <b>{DAILY_BONUS_AMOUNT} so'm</b>\n"
        f"📦 Joriy balans: <b>{new_balance} so'm</b>\n"
        f"📅 Dastur kuni: <b>{program_day}/{DAILY_BONUS_DAYS}</b>\n"
        f"🔥 Ketma-ket bonus kuni: <b>{streak_day}</b>\n"
        f"⏳ Tugashigacha qolgan kunlar: <b>{days_left}</b>\n\n"
        "<b>Kalendar:</b>\n"
        f"<code>{calendar}</code>",
        parse_mode=ParseMode.HTML,
    )
