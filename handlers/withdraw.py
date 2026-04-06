from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest # Xatolarni boshqarish uchun
from datetime import date
from config import ADMIN_ID
from database import get_db_pool

router = Router()

# 💸 FSM — pul yechish
class WithdrawState(StatesGroup):
    card = State()
    amount = State()

MIN_WITHDRAW = 60000
MAX_WITHDRAW = 100000
PAYOUT_DAY = 2

def _next_payout_date(today: date) -> date:
    if today.day < PAYOUT_DAY:
        return today.replace(day=PAYOUT_DAY)

    if today.month == 12:
        return date(today.year + 1, 1, PAYOUT_DAY)

    return date(today.year, today.month + 1, PAYOUT_DAY)


# ------------------ Pul yechish ------------------
@router.message(F.text == "💰 Pul yechish")
async def withdraw_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT balance, blocked, pending_withdraw FROM users WHERE user_id = $1",
            message.from_user.id
        )

    if not user:
        return await message.answer("Siz hali ro‘yxatdan o‘tmagansiz.")
    if user['blocked'] == 1:
        return await message.answer("🚫 Sizning akkauntingiz bloklangan.")
    if user['pending_withdraw']:
        return await message.answer("⏳ Sizda avvalgi pul yechish so‘rovi tekshirilmoqda.")

    today = date.today()
    if today.day != PAYOUT_DAY:
        next_payout = _next_payout_date(today)
        days_left = (next_payout - today).days

        if days_left == 1:
            wait_text = "1 kun"
        else:
            wait_text = f"{days_left} kun"

        return await message.answer(
            "🎉 <b>To'lov marafoni har oyning 2-sanasi bo'ladi!</b>\n\n"
            "💡 Hozirdan tayyorlaning: balansingizni oshirib boring.\n"
            f"🗓 Keyingi to'lov kuni: <b>{next_payout.strftime('%d.%m.%Y')}</b>\n"
            f"⏳ Qolgan vaqt: <b>{wait_text}</b>\n\n"
            "🚀 2-sanada so'rov yuborsangiz, tezkor ko'rib chiqiladi.",
            parse_mode=ParseMode.HTML,
        )
    
    if user['balance'] < MIN_WITHDRAW:
        return await message.answer(f"❗ Pul yechish uchun kamida <b>{MIN_WITHDRAW:,} so‘m</b> kerak.")

    await message.answer("💳 Karta raqamingizni kiriting (masalan: 8600 1234 5678 9999):")
    await state.set_state(WithdrawState.card)


@router.message(WithdrawState.card)
async def get_card_number(message: types.Message, state: FSMContext):
    card = message.text.strip()
    if not card.replace(" ", "").isdigit() or len(card.replace(" ", "")) not in [16, 20]:
        return await message.answer("❌ Noto‘g‘ri karta raqami. Qayta kiriting:")
    await state.update_data(card=card)
    await message.answer("💰 Endi yechmoqchi bo‘lgan summani kiriting:")
    await state.set_state(WithdrawState.amount)


@router.message(WithdrawState.amount)
async def get_withdraw_amount(message: types.Message, state: FSMContext):
    bot = message.bot
    data = await state.get_data()
    card = data['card']
    try:
        amount = int(message.text.strip())
    except ValueError:
        return await message.answer("❌ Faqat raqam kiriting.")

    if not (MIN_WITHDRAW <= amount <= MAX_WITHDRAW):
        return await message.answer(f"❗ Summani {MIN_WITHDRAW:,} — {MAX_WITHDRAW:,} oralig‘ida kiriting.")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", message.from_user.id)
    if amount > user['balance']:
        return await message.answer("❌ Hisobingizda yetarli mablag‘ yo‘q.")

    # 🛑 MUHIM O'ZGARTIRISH: Callback data'ga 'withdraw_' prefiksi qo'shildi
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"withdraw_approve_{message.from_user.id}_{amount}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"withdraw_reject_{message.from_user.id}")
        ]
    ])
    
    await bot.send_message(
        ADMIN_ID,
        f"💸 <b>Yangi pul yechish so‘rovi!</b>\n"
        f"👤 ID: <code>{message.from_user.id}</code>\n"
        f"💳 Karta: <code>{card}</code>\n"
        f"💰 So‘ralgan summa: <b>{amount} so‘m</b>",
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )
    
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET pending_withdraw = TRUE WHERE user_id = $1", message.from_user.id)

    await message.answer("🕐 So‘rovingiz yuborildi. Iltimos, tasdiqlanishini kuting.")
    await state.clear()


@router.callback_query(F.data.startswith("withdraw_approve_"))
async def approve_payout(callback: types.CallbackQuery):
    bot = callback.bot
    # 🛑 O'ZGARTIRISH: Prefiks qo'shilgani uchun birinchi elementni e'tiborsiz qoldiramiz
    _, _, user_id, amount = callback.data.split("_")
    
    try:
        user_id, amount = int(user_id), int(amount)
    except ValueError:
        await callback.answer("Noto'g'ri ma'lumot formati.", show_alert=True)
        return
        
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            user = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", user_id)
            if user and user['balance'] >= amount:
                await conn.execute(
                    "UPDATE users SET balance = balance - $1, pending_withdraw = FALSE WHERE user_id = $2",
                    amount,
                    user_id
                )
                
                # Userga xabar yuborish (Xatolarni boshqarish bilan)
                try:
                    await bot.send_message(user_id, f"✅ <b>{amount:,} so‘m</b> to‘lov amalga oshirildi 💸", parse_mode=ParseMode.HTML)
                except TelegramBadRequest as e:
                    if "chat not found" in str(e):
                        print(f"User {user_id} blocked the bot. Payout approved, but message failed.")
                
                await callback.message.edit_text(f"✅ To‘lov tasdiqlandi!\n🆔 ID: {user_id}\n💰 {amount:,} so‘m")
                await callback.answer("To‘lov tasdiqlandi.")
            else:
                # Userga xabar yuborish (Xatolarni boshqarish bilan)
                try:
                    await bot.send_message(user_id, "❌ Hisobingizda yetarli mablag‘ yo‘q.", parse_mode=ParseMode.HTML)
                except TelegramBadRequest as e:
                    if "chat not found" in str(e):
                         print(f"User {user_id} blocked the bot. Payout approval failed due to balance.")
                         
                await callback.message.edit_text("❌ To‘lov amalga oshmadi — balans yetarli emas.")
                await callback.answer("To‘lov amalga oshmadi.")


@router.callback_query(F.data.startswith("withdraw_reject_"))
async def reject_payout(callback: types.CallbackQuery):
    bot = callback.bot
    # 🛑 O'ZGARTIRISH: Prefiks qo'shilgani uchun callbackni ajratish
    try:
        # data: withdraw_reject_USER_ID -> 3 qism. 2-index user_id
        user_id = int(callback.data.split("_")[2]) 
    except (IndexError, ValueError):
        await callback.answer("Noto'g'ri callback ma'lumoti.", show_alert=True)
        return
        
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Baza holatini o'zgartirish
        await conn.execute("UPDATE users SET pending_withdraw = FALSE WHERE user_id = $1", user_id)

    # 🛑 MUAMMONI YECHISH UCHUN TRY...EXCEPT BLOKI
    try:
        await bot.send_message(user_id, "❌ Sizning pul yechish so‘rovingiz bekor qilindi.")
    except TelegramBadRequest as e:
        # Agar foydalanuvchi botni bloklagan bo'lsa
        if "chat not found" in str(e):
            print(f"User {user_id} blocked the bot. Cannot send rejection message.")
        else:
            # Boshqa noma'lum xatolik
            print(f"Error sending message to {user_id}: {e}")
            
    # Admin xabarini yangilash
    await callback.message.edit_text(f"❌ Pul yechish so‘rovi bekor qilindi.\n🆔 User ID: {user_id}")
    await callback.answer("So'rov muvaffaqiyatli bekor qilindi.", show_alert=False)