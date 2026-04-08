from aiogram import F, Router, types
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import ADMIN_ID
from database import get_db_pool
from utils.states import BonusChangeState

admin_bonus_router = Router()

TARGET_REF = "ref"
TARGET_GROUP = "group"


def _target_title(target: str) -> str:
    return "Referal" if target == TARGET_REF else "Guruh"


async def _get_bonus_deltas(conn) -> tuple[int, int]:
    row = await conn.fetchrow(
        "SELECT referral_bonus_delta, group_bonus_delta FROM bonus_config WHERE id = 1"
    )
    if not row:
        return 0, 0
    return int(row["referral_bonus_delta"] or 0), int(row["group_bonus_delta"] or 0)


@admin_bonus_router.message(F.text.startswith("/changebonus"))
async def change_bonus_menu(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Siz admin emassiz.")

    await state.clear()

    buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Referal bonusini o'zgartirish", callback_data="bonus_target_ref")],
            [InlineKeyboardButton(text="👥 Guruh bonusini o'zgartirish", callback_data="bonus_target_group")],
        ]
    )

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        ref_delta, group_delta = await _get_bonus_deltas(conn)

    await message.answer(
        "⚙️ <b>Bonusni o'zgartirish menyusi</b>\n\n"
        f"Joriy referal delta: <b>{ref_delta:+d}</b>\n"
        f"Joriy guruh delta: <b>{group_delta:+d}</b>\n\n"
        "Qaysi yo'nalishni o'zgartirmoqchisiz?",
        parse_mode=ParseMode.HTML,
        reply_markup=buttons,
    )


@admin_bonus_router.callback_query(F.data.startswith("bonus_target_"))
async def choose_bonus_target(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ Ruxsat yo'q", show_alert=True)

    target = TARGET_REF if callback.data.endswith("ref") else TARGET_GROUP

    await state.update_data(target=target)
    await state.set_state(BonusChangeState.waiting_for_delta)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        ref_delta, group_delta = await _get_bonus_deltas(conn)

    current_delta = ref_delta if target == TARGET_REF else group_delta

    await callback.message.edit_text(
        "⚙️ <b>Bonus deltasi kiritish</b>\n\n"
        f"Tanlangan yo'nalish: <b>{_target_title(target)}</b>\n"
        f"Joriy delta: <b>{current_delta:+d}</b>\n\n"
        "Summa kiriting (masalan: <code>500</code> yoki <code>-300</code>).\n"
        "Kiritilgan qiymat mavjud deltaga qo'shiladi.",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@admin_bonus_router.message(BonusChangeState.waiting_for_delta)
async def apply_bonus_delta(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return await message.answer("❌ Siz admin emassiz.")

    raw_value = (message.text or "").strip().replace(" ", "")
    try:
        delta_change = int(raw_value)
    except ValueError:
        return await message.answer("❌ Noto'g'ri format. Masalan: 500 yoki -300")

    data = await state.get_data()
    target = data.get("target")
    if target not in {TARGET_REF, TARGET_GROUP}:
        await state.clear()
        return await message.answer("❌ Yo'nalish topilmadi. /changebonus ni qayta yuboring.")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if target == TARGET_REF:
            row = await conn.fetchrow(
                """
                UPDATE bonus_config
                SET referral_bonus_delta = referral_bonus_delta + $1,
                    updated_at = now()
                WHERE id = 1
                RETURNING referral_bonus_delta, group_bonus_delta
                """,
                delta_change,
            )
        else:
            row = await conn.fetchrow(
                """
                UPDATE bonus_config
                SET group_bonus_delta = group_bonus_delta + $1,
                    updated_at = now()
                WHERE id = 1
                RETURNING referral_bonus_delta, group_bonus_delta
                """,
                delta_change,
            )

    ref_delta = int(row["referral_bonus_delta"] or 0)
    group_delta = int(row["group_bonus_delta"] or 0)
    active_delta = ref_delta if target == TARGET_REF else group_delta

    await message.answer(
        "✅ <b>Bonus deltasi yangilandi</b>\n\n"
        f"Yo'nalish: <b>{_target_title(target)}</b>\n"
        f"Qo'shilgan o'zgarish: <b>{delta_change:+d}</b>\n"
        f"Yangi delta: <b>{active_delta:+d}</b>\n\n"
        f"Joriy referal delta: <b>{ref_delta:+d}</b>\n"
        f"Joriy guruh delta: <b>{group_delta:+d}</b>",
        parse_mode=ParseMode.HTML,
    )

    await state.clear()


@admin_bonus_router.message(F.text.startswith("/showbonus"))
async def show_bonus_deltas(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Siz admin emassiz.")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        ref_delta, group_delta = await _get_bonus_deltas(conn)

    await message.answer(
        "📊 <b>Joriy bonus delta holati</b>\n\n"
        f"🔗 Referal delta: <b>{ref_delta:+d}</b>\n"
        f"👥 Guruh delta: <b>{group_delta:+d}</b>",
        parse_mode=ParseMode.HTML,
    )
