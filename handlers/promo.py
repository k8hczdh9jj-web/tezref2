from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from utils.channel_check import is_member_channel_2
from config import CHANNEL_USERNAME_2, ADMIN_ID
from database import get_db_pool
from asyncpg import UniqueViolationError


router = Router()


# FSM for Promo Code
class PromoState(StatesGroup):
    waiting_for_code = State()


# 🎁 Promokod bo‘limi
@router.message(F.text.lower() == "🎁 promokod")
async def show_promocode_menu(message: types.Message):
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 Promokodni olish", url=f"https://t.me/{CHANNEL_USERNAME_2.replace('@','')}")],
        [InlineKeyboardButton(text="✏️ Promokodni terish", callback_data="enter_promo")]
    ])
    await message.answer("🎁 Promokod bo‘limi:", reply_markup=buttons)


# Promokod kiritishni boshlash
@router.callback_query(lambda c: c.data == "enter_promo")
async def enter_promo(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME_2, user_id)
        if member.status in ['left', 'kicked']:
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME_2.replace('@','')}")]
            ])
            await callback.message.edit_text(
                "⚠️ Promokodni kiritish uchun kanalga a’zo bo‘ling:",
                reply_markup=markup
            )
            return
    except:
        await callback.message.edit_text(
            "⚠️ Kanalga a'zoligingizni tekshirib bo‘lmadi.",
            reply_markup=None
        )
        return

    await callback.message.edit_text(
        "✏️ Iltimos, kanaldan olgan promokodingizni kiriting:",
        reply_markup=None
    )
    await state.set_state(PromoState.waiting_for_code)


# Promokodni qabul qilish
@router.message(PromoState.waiting_for_code)
async def claim_promo_fsm(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    user_id = message.from_user.id

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        promo = await conn.fetchrow("SELECT * FROM promo_codes WHERE code=$1 AND active=TRUE", code)
        if not promo:
            await state.clear()
            return await message.answer("❌ Bunday aktiv promokod topilmadi.")

        async with conn.transaction():
            already = await conn.fetchval("SELECT 1 FROM promo_claims WHERE code=$1 AND user_id=$2", code, user_id)
            if already:
                await state.clear()
                return await message.answer("❌ Siz ushbu promokodni allaqachon ishlatgansiz.")

            row = await conn.fetchrow("""
                UPDATE promo_codes SET uses_left = uses_left - 1
                WHERE code=$1 AND uses_left > 0
                RETURNING amount, uses_left
            """, code)
            if not row:
                await state.clear()
                return await message.answer("❌ Afsuski, promokod tugab qolgan.")

            await conn.execute("INSERT INTO promo_claims(code, user_id) VALUES($1,$2)", code, user_id)
            await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", row['amount'], user_id)

    await message.answer(f"🎉 Tabriklaymiz! Sizga {row['amount']} so'm qo‘shildi!")
    await state.clear()


# Admin uchun promokod yaratish komandasi
@router.message(F.text.startswith("/createpromo"))
async def create_promo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Bu buyruq faqat adminlarga.")

    parts = message.text.split()
    if len(parts) < 4:
        return await message.answer("Foydalanish: /createpromo CODE AMOUNT MAX_USES")

    code = parts[1].upper()
    try:
        amount = int(parts[2])
        max_uses = int(parts[3])
    except ValueError:
        return await message.answer("❌ Amount va MAX_USES son bo‘lishi kerak.")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute("""
                INSERT INTO promo_codes(code, amount, max_uses, uses_left, created_by)
                VALUES($1, $2, $3, $3, $4)
            """, code, amount, max_uses, message.from_user.id)
        except UniqueViolationError:
            return await message.answer("❌ Bunday kod mavjud.")

    await message.answer(f"✅ Promokod {code} yaratildi: {amount} so'm, {max_uses} ta ishlash mumkin.")
