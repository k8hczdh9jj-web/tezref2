import re
from aiogram import Router, types, F, Bot
from aiogram.types import (
    KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from database import get_db_pool
from utils.levels import get_team_level 
from math import ceil
from datetime import datetime, timedelta

# Eslatma: 'handlers.start' dan importni bu yerga kiritishdan oldin, 
# 'start.py' da ham 'team.py' ga bog'liqlik bo'lsa, aylana import (circular import) yuzaga kelmasligi uchun 
# 'process_team_invite' funksiyasi ichida funksiyani import qilish mantiqini saqlab qolamiz.

team_router = Router()

BANNED_WORDS = ["yolg'on", "mashenikla", "mashenik", "mashka"]
TEAMS_PER_PAGE = 10

class CreateTeamFSM(StatesGroup):
    waiting_for_name = State()

class CoinConvertState(StatesGroup):
    waiting_amount = State()

# --- MENYULAR (KEYBOARDS) ---

def team_menu(user_in_team: bool = False):
    """Asosiy jamoa menyusi"""
    kb = []
    if not user_in_team:
        kb.append([KeyboardButton(text="➕ Yangi jamoa yaratish")])
        kb.append([KeyboardButton(text="📋 Jamoa tanlash")])
        kb.append([KeyboardButton(text="🏆 Jamoalar reytingi")])
    else:
        kb.append([KeyboardButton(text="👥 Mening jamoam")])
        kb.append([KeyboardButton(text="📋 Jamoa tanlash")])
        kb.append([KeyboardButton(text="🏆 Jamoalar reytingi")])
    
    kb.append([KeyboardButton(text="🔙 Ortga")]) 
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def my_team_menu(is_leader: bool = False, pending_requests_count: int = 0):
    """Mening jamoam menyusi, liderlar uchun arizalar tugmasini o'z ichiga oladi"""
    kb = [
        [KeyboardButton(text="🛒 Shop"), KeyboardButton(text="🔄 Tanga sotib olish")],
        [KeyboardButton(text="👥 Odam qo'shish")],
    ]
    
    if is_leader:
        request_text = "📥 Arizalar"
        if pending_requests_count > 0:
            request_text += f" ({pending_requests_count})"
        kb.append([KeyboardButton(text=request_text)])
    
    kb.append([KeyboardButton(text="❌ Jamoadan chiqish"), KeyboardButton(text="⬅️ Jamoa menyusi")]) 
    
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- JAMOANI OCHISH ---

@team_router.message(F.text == "👥 Jamoa")
async def open_team_menu(message: types.Message):
    user_id = message.from_user.id
    pool = await get_db_pool()
    user = await pool.fetchrow("SELECT team_id FROM users WHERE user_id = $1", user_id)
    in_team = user and user['team_id'] is not None
    await message.answer("Jamoa menyusi:", reply_markup=team_menu(in_team))

# --- YANGI JAMOA YARATISH ---

@team_router.message(F.text == "➕ Yangi jamoa yaratish")
async def start_create_team(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    pool = await get_db_pool()
    user = await pool.fetchrow("SELECT referrals, team_id FROM users WHERE user_id=$1", user_id)
    
    if not user:
        return await message.answer("Siz ro'yxatdan o'tmagansiz.")
    if user['team_id']:
        return await message.answer("❌ Siz allaqachon jamoada ishtirokchisiz.")
    if (user['referrals'] or 0) < 10:
        return await message.answer("❌ Jamoa yaratish uchun kamida 10 ta referalingiz bo‘lishi kerak.")
        
    await state.set_state(CreateTeamFSM.waiting_for_name)
    await message.answer("Jamoa nomini kiriting (noqulay so‘z ishlatmang):", reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Ortga")]], resize_keyboard=True
    ))

@team_router.message(CreateTeamFSM.waiting_for_name)
async def process_team_name(message: types.Message, state: FSMContext, bot: Bot):
    team_name = message.text.strip()
    user_id = message.from_user.id
    
    if team_name == "🔙 Ortga":
        await state.clear()
        return await open_team_menu(message)
    
    if any(word in team_name.lower() for word in BANNED_WORDS):
        await state.clear()
        return await message.answer("❌ Nomaqbul so‘z ishlatildi.", reply_markup=team_menu())
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        try:
            team_id = await conn.fetchval(
                """INSERT INTO teams (team_name, creator_id, creator_username, members_count, team_coins) 
                    VALUES ($1, $2, $3, 1, 4) RETURNING team_id""",
                team_name, user_id, message.from_user.username or ""
            )
            invite_link = f"https://t.me/{(await bot.get_me()).username}?start=team_{team_id}" 
            await conn.execute("UPDATE teams SET invite_link=$1 WHERE team_id=$2", invite_link, team_id)
            await conn.execute("UPDATE users SET team_id=$1, total_team_contribution=total_team_contribution + 4 WHERE user_id=$2", team_id, user_id) 
            await conn.execute("INSERT INTO team_members (team_id, user_id) VALUES ($1, $2)", team_id, user_id)
        except Exception as e:
            if "unique" in str(e).lower():
                await state.clear()
                return await message.answer("❌ Bunday nomli jamoa mavjud.", reply_markup=team_menu())
            await state.clear()
            return await message.answer(f"❌ Xatolik yuz berdi. {e}", reply_markup=team_menu())
            
    await state.clear()
    await message.answer(
        f"✅ Jamoa yaratildi!\n<b>{team_name}</b>\nInvite: {invite_link}",
        reply_markup=my_team_menu(is_leader=True, pending_requests_count=0),
        parse_mode=ParseMode.HTML
    )
    await show_my_team_info(message)

# --- MENING JAMOAM ---

@team_router.message(F.text == "👥 Mening jamoam")
async def my_team_entry(message: types.Message):
    user_id = message.from_user.id
    pool = await get_db_pool()
    
    is_leader = await pool.fetchval("SELECT 1 FROM teams WHERE creator_id = $1", user_id)
    pending_count = 0
    
    if is_leader:
        # Userning jamoa ID sini topish
        team_id = await pool.fetchval("SELECT team_id FROM teams WHERE creator_id = $1", user_id)
        if team_id:
            pending_count = await pool.fetchval("SELECT COUNT(*) FROM team_requests WHERE team_id = $1 AND request_status = 'pending'", team_id)
    
    await message.answer("👥 Mening jamoam bo'limi:", reply_markup=my_team_menu(is_leader, pending_count))
    await show_my_team_info(message)

async def show_my_team_info(message: types.Message):
    user_id = message.from_user.id
    pool = await get_db_pool()
    
    data = await pool.fetchrow("""
        SELECT u.team_id, t.team_name, t.creator_id, t.creator_username, t.members_count, t.team_coins 
        FROM users u
        JOIN teams t ON u.team_id = t.team_id
        WHERE u.user_id = $1
    """, user_id)
    
    if not data:
        return await message.answer("Siz jamoaga ulanmagansiz.", reply_markup=team_menu(False))
    
    # 🌟 YENGI QISM: Jamoa darajasini hisoblash
    team_level = get_team_level(data['members_count'])

    if data['creator_username']:
        lider_text = f"@{data['creator_username']}"
    else:
        lider_text = f"<a href='tg://user?id={data['creator_id']}'>Lider (ID: {data['creator_id']})</a>"
        
    collection = "🎁" * 3
    
# --- TOP 5 DONATORLAR ---
    top_donators = await pool.fetch("""
        SELECT username, total_team_contribution, user_id
        FROM users 
        WHERE team_id = $1 
        ORDER BY total_team_contribution DESC 
        LIMIT 5
    """, data['team_id'])
    
    donators_text = "\n\n🏆 <b>TOP 5 Donatorlar:</b>\n"
    
    if top_donators:
        for i, d in enumerate(top_donators, 1):
            display_name = d['username'] if d['username'] else f"ID: {d['user_id']}"
            if d['user_id'] == user_id and not d['username']:
                display_name = f"<a href='tg://user?id={d['user_id']}'>Siz</a>"
                
            donators_text += f"   {i}. {display_name}: {d['total_team_contribution']} tanga\n"
    else:
        donators_text += "   <i>Hozircha hech kim hissa qo‘shmagan.</i>"
    # --- TOP 5 DONATORLAR YAKUNI ---
    
    text = (
        f"🛡 <b>Jamoa Nomi:</b> {data['team_name']}\n"
        f"✨ <b>Daraja:</b> {team_level}\n"  # 🌟 Daraja kiritildi
        f"👑 <b>Lider:</b> {lider_text}\n"
        f"👥 <b>Azolar soni:</b> {data['members_count']}\n"
        f"💰 <b>Xazina:</b> {data['team_coins']} tanga\n"
        f"🏺 <b>Kolleksiya:</b> {collection}\n"
    )
    
    text += donators_text

    await message.answer(text, parse_mode=ParseMode.HTML)

# --- ODAM QO'SHISH TUGMASI ---

@team_router.message(F.text == "👥 Odam qo'shish")
async def get_team_invite_link(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    pool = await get_db_pool()
    
    team_data = await pool.fetchrow("""
        SELECT t.team_name, t.invite_link
        FROM users u
        JOIN teams t ON u.team_id = t.team_id
        WHERE u.user_id = $1
    """, user_id)
    
    if not team_data:
        return await message.answer("Siz jamoaga ulanmagansiz.")
    
    invite_link = team_data['invite_link']
    team_name = team_data['team_name']
    
    # Matn Ariza yuborish mantiqiga moslab o'zgartirildi
    share_text = f"Men **{team_name}** jamoasiga qo'shilish uchun ariza yubordim! Siz ham qo'shiling:\n🔗 {invite_link}"
    
    text = (
        f"🔗 **{team_name}** jamoasiga do'stlarni taklif qilish havolasi:\n\n"
        f"Bu havolani do'stingizga yuboring. Ular botga kirishi bilan to‘g‘ridan-to‘g‘ri jamoa sahifasiga yo‘naltiriladi va u yerdan **qo'shilish uchun ariza yuborishi** mumkin.\n\n"
        f"**Havola:** <code>{invite_link}</code>"
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↗️ Havolani ulashish", switch_inline_query=share_text)]
    ])
    
    await message.answer(
        text, 
        reply_markup=markup, 
        parse_mode=ParseMode.HTML
    )

# --- JAMOA ICHKI TUGMALARI (O'zgarishsiz) ---

@team_router.message(F.text == "🛒 Shop")
async def show_team_shop_text(message: types.Message):
    await message.answer("🛒 Shop funksiyasi tez kunda!")

@team_router.message(F.text == "❌ Jamoadan chiqish")
async def ask_leave_team_text(message: types.Message):
    user_id = message.from_user.id
    pool = await get_db_pool()
    
    is_creator = await pool.fetchval("""
        SELECT 1 FROM teams WHERE creator_id = $1 AND team_id = (SELECT team_id FROM users WHERE user_id=$1)
    """, user_id)
    
    if is_creator:
        return await message.answer("⛔️ Siz jamoa liderisiz! Chiqib keta olmaysiz. Chiqib ketish uchun adminga murojaat qiling")

    text = "⚠️ Jamoani tark etsangiz, 5 kun davomida boshqa jamoaga qo‘shila olmaysiz.\nChiqishni istaysizmi?"
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, chiqaman", callback_data="do_leave_team")],
        [InlineKeyboardButton(text="❌ Yo‘q, chiqmayman", callback_data="cancel_leave_team")],
    ])
    await message.answer(text, reply_markup=ikb)

@team_router.message(F.text == "⬅️ Jamoa menyusi")
async def back_to_team_menu_handler(message: types.Message):
    await open_team_menu(message)

@team_router.callback_query(F.data == "do_leave_team")
async def do_leave_team(callback: CallbackQuery):
    user_id = callback.from_user.id
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT team_id FROM users WHERE user_id=$1", user_id)
        if not user or not user["team_id"]:
            return await callback.message.edit_text("Siz jamoada emassiz.")
        
        is_creator = await conn.fetchval("SELECT 1 FROM teams WHERE team_id=$1 AND creator_id=$2", user['team_id'], user_id)
        if is_creator:
             return await callback.message.edit_text("❌ Liderlar jamoadan chiqa olmaydi.")

        await conn.execute("UPDATE users SET team_id=NULL, left_team_at=$1 WHERE user_id=$2", datetime.now(), user_id)
        await conn.execute("UPDATE teams SET members_count = GREATEST(members_count - 1, 0) WHERE team_id=$1", user["team_id"])
        await conn.execute("DELETE FROM team_members WHERE user_id=$1", user_id)
        
    await callback.message.edit_text("✅ Siz jamoani tark etdingiz!\nYangi jamoaga 5 kun o‘tibgina qo‘shila olasiz.")
    await callback.message.answer("Jamoa menyusi:", reply_markup=team_menu(user_in_team=False))

@team_router.callback_query(F.data == "cancel_leave_team")
async def cancel_leave_team(callback: CallbackQuery):
    await callback.answer() # callbackga javob qaytarish
    await callback.message.delete()

# --- TANGA KONVERTATSIYA (O'zgarishsiz) ---

@team_router.message(F.text == "🔄 Tanga sotib olish")
async def ask_convert_amount(message: types.Message, state: FSMContext):
    await message.answer(
        "Jamoa xazinasi uchun qancha so‘m o‘tkazmoqchisiz?\n<i>(1000 so‘m = 15 tanga )</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Bekor qilish")]], resize_keyboard=True)
    )
    await state.set_state(CoinConvertState.waiting_amount)

@team_router.message(CoinConvertState.waiting_amount)
async def convert_coins(message: types.Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=my_team_menu())

    try:
        amount = int(message.text.strip())
    except ValueError:
        return await message.answer("Faqat raqam kiriting.")
    
    if amount < 1000 or amount % 1000 != 0:
        return await message.answer("Minimal summa 1000 so‘m.")
        
    user_id = message.from_user.id
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT balance, team_id FROM users WHERE user_id=$1", user_id)
        if not user or not user['team_id']:
            return await message.answer("Siz jamoaga ulanmagansiz.", reply_markup=team_menu(False))
        if (user['balance'] or 0) < amount:
            return await message.answer(f"Mablag‘ yetarli emas. Sizda: {user['balance'] or 0} so‘m.")
            
        coins = (amount // 1000) * 15
        
        await conn.execute("UPDATE users SET balance = balance - $1, total_team_contribution = total_team_contribution + $2 WHERE user_id=$3", amount, coins, user_id)
        await conn.execute("UPDATE teams SET team_coins = team_coins + $1 WHERE team_id=$2", coins, user['team_id'])
        await conn.execute("""
            INSERT INTO team_transactions 
            (user_id, team_id, amount_money, amount_coins, created_at) 
            VALUES ($1, $2, $3, $4, NOW())
        """, user_id, user['team_id'], amount, coins)
        
    await message.answer(f"✅ **{amount} so‘m {coins} tanga sifatida o'tkazildi!**", reply_markup=my_team_menu(), parse_mode=ParseMode.HTML)
    await show_my_team_info(message) 
    await state.clear()

# --- JAMOA TANLASH VA SAHIFALASH (O'zgarishsiz) ---

@team_router.message(F.text == "📋 Jamoa tanlash")
async def show_teams(message: types.Message):
    await show_teams_page(message, page=0)

@team_router.callback_query(F.data.regexp(r"^teams_page_\d+$"))
async def paginate_teams(callback: CallbackQuery):
    page = int(callback.data.removeprefix("teams_page_"))
    await show_teams_page(callback.message, page, edit=True)
    await callback.answer()

async def show_teams_page(msg, page: int, edit=False):
    pool = await get_db_pool()
    total = await pool.fetchval("SELECT COUNT(*) FROM teams")
    
    teams = await pool.fetch(
        "SELECT team_id, team_name, team_coins, members_count FROM teams ORDER BY team_coins DESC LIMIT $1 OFFSET $2",
        TEAMS_PER_PAGE, page*TEAMS_PER_PAGE
    )
    
    if not teams:
        text = "Hozircha jamoalar mavjud emas."
        markup = None
    else:
        text = "📋 <b>Jamoangizni tanlang!:</b>" 
        rows = []
        start_index = page * TEAMS_PER_PAGE + 1
        
        for num, t in enumerate(teams, start_index):
            btn_text = f"{num}. {t['team_name']} - {t['team_coins']} tanga ({t['members_count']} a’zo)\n"
            rows.append([InlineKeyboardButton(text=btn_text, callback_data=f"view_team_{t['team_id']}")])
        
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"teams_page_{page-1}"))
        if (page+1)*TEAMS_PER_PAGE < total:
            nav_row.append(InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"teams_page_{page+1}"))
        
        if nav_row:
            rows.append(nav_row)
            
        markup = InlineKeyboardMarkup(inline_keyboard=rows)
        
    if edit:
        await msg.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await msg.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)

# ----------------------------------------------------------
# 🔄 JAMOA STATISTIKASI VA ARIZA YUBORISH
# ----------------------------------------------------------

@team_router.callback_query(F.data.regexp(r"^view_team_\d+$"))
async def view_team_stats(callback: CallbackQuery):
    team_id = int(callback.data.removeprefix("view_team_"))
    await view_team_by_id_from_callback(callback, team_id, edit=True)

async def view_team_by_id_from_callback(callback: CallbackQuery, team_id: int, edit: bool = True):
    """Callback orqali kelgan userga jamoa ma'lumotlarini ko'rsatadi."""
    user_id = callback.from_user.id
    pool = await get_db_pool()

    team = await pool.fetchrow("SELECT * FROM teams WHERE team_id=$1", team_id)
    if not team:
        await callback.answer("Jamoa topilmadi.", show_alert=True)
        return

    user = await pool.fetchrow("SELECT team_id FROM users WHERE user_id=$1", user_id)
    in_any_team = user and user['team_id'] is not None

    # Userning bu jamoaga arizasi bormi tekshirish
    request_exists = await pool.fetchval(
        "SELECT 1 FROM team_requests WHERE user_id = $1 AND team_id = $2 AND request_status = 'pending'",
        user_id, team_id
    )
    
    team_level = get_team_level(team['members_count'])

    if team['creator_username']:
        lider_text = f"@{team['creator_username']}"
    else:
        lider_text = f"ID: {team['creator_id']}"
        
    collection = "🎁" * 3 
    
    text = (
        f"🛡 <b>Jamoa:</b> {team['team_name']}\n"
        f"✨ <b>Daraja:</b> {team_level}\n"
        f"👑 <b>Lider:</b> {lider_text}\n"
        f"👥 <b>A'zolar:</b> {team['members_count']} a’zo\n"
        f"💰 <b>Xazina:</b> {team['team_coins']} tanga\n"
        f"🏺 <b>Kolleksiya:</b> {collection}\n"
    )
    
    kb = []
    
    if in_any_team:
        text += "\n\n❌ Siz allaqachon boshqa jamoaga qo'shilgansiz."
    elif request_exists:
        kb.append([InlineKeyboardButton(text="⏳ Ariza yuborilgan", callback_data="none")])
    else:
        # Ariza yuborish tugmasi
        kb.append([InlineKeyboardButton(text="➕ Jamoaga qo‘shilish uchun ariza", callback_data=f"apply_team_{team_id}")]) 
    
    kb.append([InlineKeyboardButton(text="🔙 Ro‘yxatga qaytish", callback_data="teams_page_0")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=kb)
    
    if edit:
        await callback.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        # Agar edit false bo'lsa (masalan, /start dan kelgan bo'lsa), yangi xabar yuboramiz
        await callback.message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    await callback.answer() # MUHIM: Har doim callbackga javob qaytarish

@team_router.callback_query(F.data.regexp(r"^apply_team_\d+$"))
async def apply_to_team_callback(callback: CallbackQuery, bot: Bot):
    """Jamoaga qo'shilish uchun ariza yuborish. Rad etilgan arizalar borligini tekshiradi va o'chiradi."""
    team_id = int(callback.data.removeprefix("apply_team_"))
    user_id = callback.from_user.id
    
    current_username = callback.from_user.username
    user_display = f"@{current_username}" if current_username else f"ID: {user_id}"

    pool = await get_db_pool()
    
    # 1. Taqiq va jamoada borlikni tekshirish
    user = await pool.fetchrow("SELECT team_id, left_team_at FROM users WHERE user_id=$1", user_id)
    if not user:
        await callback.answer("Ro'yxatdan o'ting!", show_alert=True)
        return
        
    if user['team_id']:
        await callback.answer("Siz allaqachon jamoada bor ekansiz.", show_alert=True)
        return
        
    if user['left_team_at']:
        left_time = user['left_team_at']
        if (datetime.now() - left_time) < timedelta(days=5):
            remaining = timedelta(days=5) - (datetime.now() - left_time)
            days = remaining.days
            hours = remaining.seconds // 3600
            await callback.answer(f"⛔️ 5 kunlik taqiq mavjud! Qolgan vaqt: {days} kun {hours} soat.", show_alert=True)
            return

    # 2. Arizani bazaga saqlash
    team = await pool.fetchrow("SELECT team_name, creator_id FROM teams WHERE team_id=$1", team_id)
    if not team:
        await callback.answer("Jamoa mavjud emas.", show_alert=True)
        return
    
    leader_id = team['creator_id']

    async with pool.acquire() as conn:
        
        # 🛑 MUHIM TUZATISH: Oldingi RAD ETILGAN arizani o'chirish/yangilash
        # Agar user oldin ariza yuborgan va u rad etilgan bo'lsa, 'duplicate key' xatosi keladi.
        # Shuning uchun, avvalgi (rad etilgan yoki hatto o'tgan) arizani o'chiramiz.
        # Eslatma: 'pending' bo'lmagan, lekin bazada yotgan yozuvni o'chirish.
        try:
             # Rad etilgan (rejected) yoki bekor qilingan (cancelled) arizalar ustidan yozish/o'chirish
             await conn.execute("""
                 DELETE FROM team_requests 
                 WHERE user_id = $1 AND team_id = $2 AND request_status != 'pending'
             """, user_id, team_id)
        except Exception as e:
            # Bu yerda xato bo'lsa ham jarayonni to'xtatmaymiz, chunki asosiy INSERT muhim
            print(f"Oldingi arizani o'chirishda xato: {e}")

        try:
            # 2. Arizani bazaga saqlash
            # Agar 'pending' ariza mavjud bo'lsa, bu yerda "duplicate key" xatosi keladi (Unique Constraint)
            await conn.execute("""
                INSERT INTO team_requests (team_id, user_id, leader_id, username, request_status) 
                VALUES ($1, $2, $3, $4, 'pending')
            """, team_id, user_id, leader_id, current_username)
            
            # 1. 📢 Foydalanuvchiga *tezkor* javob qaytarish (zagruzkani yo'qotish)
            await callback.answer(f"✅ Ariza {team['team_name']} jamoasi lideriga yuborildi.", show_alert=True)

            # 2. ✏️ Tugmani yangilash 
            await callback.message.edit_reply_markup(
                InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏳ Ariza yuborilgan", callback_data="none")],
                    [InlineKeyboardButton(text="🔙 Ro‘yxatga qaytish", callback_data="teams_page_0")]
                ])
            )

            # 3. 📧 Liderga xabar yuborish
            leader_msg = (
                f"📥 Yangi Ariza!\n"
                f"User: {user_display} **{team['team_name']}** jamoangizga qo‘shilish uchun ariza yubordi."
            )
            leader_markup = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"team_accept_{team_id}_{user_id}"),
                    InlineKeyboardButton(text="❌ Rad etish", callback_data=f"team_reject_{team_id}_{user_id}")
                ]
            ])
            await bot.send_message(leader_id, leader_msg, reply_markup=leader_markup, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            # Xato yuz berganda ham doimo javob qaytarish
            if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
                # Duplicate entry holatida (allaqachon pending ariza yuborilgan)
                await callback.answer("❌ Siz allaqachon **kutilayotgan** ariza yuborgansiz.", show_alert=True)
            else:
                # Boshqa kutilmagan xato holatida
                await callback.answer(f"❌ Kutilmagan xatolik yuz berdi. {e}", show_alert=True)
                print(f"Error applying to team: {e}")

    # Eslatma: Barcha ehtimoliy yo'llarda (if/else, try/except) callback.answer() chaqirilganligi uchun, 
    # funksiya oxirida qo'shimcha callback.answer() talab qilinmaydi.

# ----------------------------------------------------------------------------------
# 🚀 DEEP LINK HANDLER (JAMOANI KO'RSATISHGA YO'NALTIRILDI)
# ----------------------------------------------------------------------------------

async def view_team_by_id_from_message(message: types.Message, team_id: int):
    """
    /start team_ID buyrug'i kelganda jamoani ko'rsatish uchun.
    """
    user_id = message.from_user.id
    pool = await get_db_pool()
    
    # 1. Tekshiruvlar (taqiq va jamoada borligi)
    user = await pool.fetchrow("SELECT team_id, left_team_at FROM users WHERE user_id=$1", user_id)
    if not user:
        # Agar user start.py da yaratilmagan bo'lsa
        await message.answer("Siz ro'yxatdan o'tishingiz kerak.")
        return

    if user['team_id']:
        await message.answer("Siz allaqachon boshqa jamoada bor ekansiz.", reply_markup=my_team_menu())
        return

    if user['left_team_at']:
        left_time = user['left_team_at']
        if (datetime.now() - left_time) < timedelta(days=5):
            remaining = timedelta(days=5) - (datetime.now() - left_time)
            days = remaining.days
            hours = remaining.seconds // 3600
            
            try:
                from .start import main_menu 
                await message.answer(f"⛔️ 5 kunlik taqiq mavjud! Qolgan vaqt: {days} kun {hours} soat.", reply_markup=main_menu()) 
            except ImportError:
                 await message.answer(f"⛔️ 5 kunlik taqiq mavjud! Qolgan vaqt: {days} kun {hours} soat.")
            
            return

    # 2. Jamoa ma'lumotlarini olish va sahifani ko'rsatish
    team = await pool.fetchrow("SELECT * FROM teams WHERE team_id=$1", team_id)
    if not team:
        try:
            from .start import main_menu 
            await message.answer("Jamoa mavjud emas. Oddiy bosh menyu yuklandi.", reply_markup=main_menu())
        except ImportError:
             await message.answer("Jamoa mavjud emas.")
        return

    # Userning arizasi bormi tekshirish
    request_exists = await pool.fetchval(
        "SELECT 1 FROM team_requests WHERE user_id = $1 AND team_id = $2 AND request_status = 'pending'",
        user_id, team_id
    )

    team_level = get_team_level(team['members_count'])

    if team['creator_username']:
        lider_text = f"@{team['creator_username']}"
    else:
        lider_text = f"ID: {team['creator_id']}"
        
    collection = "🎁" * 3 
    
    text = (
        f"🛡 <b>Jamoa:</b> {team['team_name']}\n"
        f"✨ <b>Daraja:</b> {team_level}\n"
        f"👑 <b>Lider:</b> {lider_text}\n"
        f"👥 <b>A'zolar:</b> {team['members_count']} a’zo\n"
        f"💰 <b>Xazina:</b> {team['team_coins']} tanga\n"
        f"🏺 <b>Kolleksiya:</b> {collection}\n"
    )
    
    kb = []
    
    if user['team_id']:
        text += "\n\n❌ Siz allaqachon boshqa jamoaga qo'shilgansiz."
    elif request_exists:
        kb.append([InlineKeyboardButton(text="⏳ Ariza yuborilgan", callback_data="none")])
    else:
        kb.append([InlineKeyboardButton(text="➕ Jamoaga qo‘shilish uchun ariza", callback_data=f"apply_team_{team_id}")]) 
    
    kb.append([InlineKeyboardButton(text="🔙 Ro‘yxatga qaytish", callback_data="teams_page_0")])
    
    markup = InlineKeyboardMarkup(inline_keyboard=kb)
    
    await message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)

    return True

async def process_team_invite(message: types.Message, team_id: int):
    """
    /start team_ID orqali kelgan foydalanuvchini jamoani ko'rsatish funksiyasiga yuboradi.
    (start.py dan chaqiriladi)
    """
    await view_team_by_id_from_message(message, team_id)
    return True

@team_router.message(F.text == "🏆 Jamoalar reytingi")
async def show_teams_rating(message: types.Message):
    """
    Jamoalar reytingini talab qilingan formatda (hamma ma'lumot bir qatorda) chiqaradi.
    """
    pool = await get_db_pool()
    
    # Tangalar soni bo'yicha kamayish tartibida TOP 10 jamoani olish
    top_teams = await pool.fetch(
        "SELECT team_name, team_coins, members_count FROM teams ORDER BY team_coins DESC LIMIT 10"
    )
    
    if not top_teams:
        return await message.answer("🏆 Hozircha reytingga kiritish uchun jamoalar yetarli emas.")

    text = "🏆 <b>Top 10 Jamoalar Reytingi<b>\n\n"
    
    # Emoji bilan chiroyli formatlash
    EMOJIS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"] 

    for i, t in enumerate(top_teams, 1):
        emoji = EMOJIS[i-1] if i <= 10 else "🏅" 
        
        # Talab qilingan format: 🥇 **1-O'rin** | **Team_A** | 💰 1500 tanga | 👥 12 a'zo
        text += (
            f"{emoji} <b>-<b> <b>{t['team_name']} jamoasi<b> | 💰 {t['team_coins']} tanga | 👥 {t['members_count']} a'zo\n"
        )
        
        # Oxirgi jamoa uchun chiziqcha qo'shmaymiz
        if i < len(top_teams):
             text += "--- \n"
    
    await message.answer(text, parse_mode=ParseMode.HTML)

@team_router.message(F.text == "🔙 Ortga")
async def back_to_main_menu(message: types.Message):
    """
    Jamoa menyusidan to'g'ridan-to'g'ri Bosh menyuga qaytaradi.
    Aylanma importni chetlab o'tish uchun funksiya ichida main_menu ni import qiladi.
    """
    try:
        # 'start.py' dan main_menu klaviatura funksiyasini import qilish
        from .start import main_menu 
        
        # Asosiy menyu klaviaturasini to'g'ridan-to'g'ri yuborish
        await message.answer("🏠 Bosh menyu:", reply_markup=main_menu()) 
        
    except ImportError:
        # Agar Import Error ro'y bersa (bu juda kam holat)
        # Foydalanuvchiga yordam bering va klaviaturani olib tashlang.
        await message.answer("Bosh menyuga qaytdingiz. Iltimos, /start buyrug‘ini bosing.", reply_markup=types.ReplyKeyboardRemove())
# -----------------------------------------------------------------
# 📥 LIDERLIK FUNKSIYALARI (ARIZALAR)
# -----------------------------------------------------------------

@team_router.message(F.text.regexp(r"^📥 Arizalar(\s\(\d+\))?$"))
async def show_pending_requests(message: types.Message):
    # Lider arizalarni ko'radi
    user_id = message.from_user.id
    pool = await get_db_pool()
    
    # Jamoani aniqlash
    team = await pool.fetchrow("SELECT team_id, team_name FROM teams WHERE creator_id = $1", user_id)
    if not team:
        return await message.answer("Siz jamoa lideri emassiz.")
        
    # Team_requests jadvalida 'username' ustuni bor deb hisoblanmoqda
    requests = await pool.fetch("""
        SELECT 
            user_id, 
            username, 
            request_id
        FROM team_requests
        WHERE team_id = $1 AND request_status = 'pending'
        ORDER BY request_id ASC
    """, team['team_id'])
    
    if not requests:
        return await message.answer("Hozircha kutilayotgan arizalar yo‘q.")

    text = f"📥 **{team['team_name']}** jamoasiga arizalar ({len(requests)} ta):\n\n"
    
    kb = []
    
    for req in requests:
        # Endi faqat username yoki ID ishlatiladi
        # 'username' ni team_requests dan olamiz (agar yuborishda saqlangan bo'lsa)
        user_display = f"@{req['username']}" if req['username'] else f"ID: {req['user_id']}"
        
        # 🛑 MUHIM O'ZGARTIRISH: Callback data'ga 'team_' prefiksi qo'shildi
        kb.append([
            InlineKeyboardButton(text=f"👤 {user_display}", callback_data=f"none"),
            InlineKeyboardButton(text="✅", callback_data=f"team_accept_{team['team_id']}_{req['user_id']}"),
            InlineKeyboardButton(text="❌", callback_data=f"team_reject_{team['team_id']}_{req['user_id']}")
        ])
        
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode=ParseMode.MARKDOWN)


# ------------------ 2. Arizani qabul qilish/rad etish funksiyasi ------------------

# 🛑 MUHIM O'ZGARTIRISH: Handler endi "team_accept_..." yoki "team_reject_..." ni tutadi
@team_router.callback_query(F.data.regexp(r"^(team_accept|team_reject)_\d+_\d+$"))
async def process_request_action(callback: CallbackQuery, bot: Bot):
    # Callback data: team_action_team_id_user_id (4 qism)
    parts = callback.data.split('_')
    
    action_type = parts[1] # accept yoki reject
    team_id_str = parts[2]
    user_id_str = parts[3]
    
    # Ma'lumot turlarini tekshirish
    try:
        team_id = int(team_id_str)
        user_to_act_on = int(user_id_str)
    except ValueError:
        await callback.answer("Xatolik: ID raqamlari noto'g'ri formatda.", show_alert=True)
        return

    leader_id = callback.from_user.id
    pool = await get_db_pool()
    
    # Lider tekshiruvi
    is_leader = await pool.fetchval("SELECT 1 FROM teams WHERE creator_id = $1 AND team_id = $2", leader_id, team_id)
    if not is_leader:
        await callback.answer("Siz bu jamoaning lideri emassiz.", show_alert=True)
        return
        
    request = await pool.fetchrow("""
        SELECT r.request_status, t.team_name, r.username 
        FROM team_requests r
        JOIN teams t ON r.team_id = t.team_id
        WHERE r.team_id = $1 AND r.user_id = $2 AND r.leader_id = $3
    """, team_id, user_to_act_on, leader_id)
    
    if not request or request['request_status'] != 'pending':
        try:
            # Tugmani o'chirish
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.answer("Bu ariza allaqachon ko'rib chiqilgan yoki topilmadi.", show_alert=True)
        return

    team_name = request['team_name']
    user_to_act_on_username = request['username']
    user_to_act_on_display = f"@{user_to_act_on_username}" if user_to_act_on_username else f"ID: {user_to_act_on}"
    
    
    user_message = ""
    leader_answer = ""
    
    if action_type == 'accept':
        # Jamoaga qo'shish mantiqi
        async with pool.acquire() as conn:
            # Tekshiruv: User allaqachon boshqa jamoada emasmi?
            user_current_team = await conn.fetchval("SELECT team_id FROM users WHERE user_id=$1", user_to_act_on)
            if user_current_team:
                try:
                    await callback.message.edit_reply_markup(reply_markup=None)
                except Exception:
                    pass
                await callback.answer("Bu user boshqa jamoaga qo'shilib bo'lgan.", show_alert=True)
                return
            
            # Baza operatsiyalari
            await conn.execute("UPDATE users SET team_id=$1, left_team_at=NULL WHERE user_id=$2", team_id, user_to_act_on)
            await conn.execute("INSERT INTO team_members (team_id, user_id) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET team_id = EXCLUDED.team_id", team_id, user_to_act_on)
            await conn.execute("UPDATE teams SET members_count = members_count + 1, team_coins = team_coins + 4 WHERE team_id=$1", team_id)
            await conn.execute("UPDATE users SET total_team_contribution = total_team_contribution + 4 WHERE user_id=$1", user_to_act_on)
            await conn.execute("UPDATE team_requests SET request_status = 'accepted' WHERE team_id = $1 AND user_id = $2", team_id, user_to_act_on)

        user_message = f"✅ Tabriklaymiz! **{team_name}** jamoasiga arizangiz qabul qilindi!"
        leader_answer = "A'zolikka qabul qilindi."
        
    elif action_type == 'reject':
        # Arizani rad etish mantiqi
        await pool.execute("UPDATE team_requests SET request_status = 'rejected' WHERE team_id = $1 AND user_id = $2", team_id, user_to_act_on)
        
        user_message = f"❌ Afsuski, **{team_name}** jamoasiga arizangiz rad etildi."
        leader_answer = "Ariza rad etildi."


    # 🛑 Userga xabar yuborish (Xatolarni to'liq boshqarish)
    try:
        # Userni o'z jamoasiga yuborish uchun funksiyalar
        from .start import main_menu # Asosiy menyu
        
        if action_type == 'accept':
            # Jamoa menyusini yuborish
            await bot.send_message(user_to_act_on, user_message, parse_mode=ParseMode.MARKDOWN, reply_markup=my_team_menu(is_leader=False)) 
            # Agar bot userga xabar yubora olmasa, bu yerda TelegramBadRequest xatosi chiqishi mumkin
        else: # reject
            # Oddiy bosh menyuni yuborish
            await bot.send_message(user_to_act_on, user_message, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu()) 
            
    except TelegramBadRequest as e:
        if "chat not found" in str(e):
             print(f"User {user_to_act_on} blocked the bot. Cannot send status message.")
        else:
            print(f"Error sending message to user {user_to_act_on}: {e}")
    except ImportError:
        # main_menu topilmagan holat
        try:
             await bot.send_message(user_to_act_on, user_message, parse_mode=ParseMode.MARKDOWN)
        except Exception:
             pass # Yana bir bor urinish
    except Exception as e:
        print(f"An unexpected error occurred during message send to user {user_to_act_on}: {e}")
        

    # Liderning xabarini yangilash
    try:
        new_text = f"User {user_to_act_on_display} arizasi: **{leader_answer}**"
        await callback.message.edit_text(new_text, reply_markup=None, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Error editing leader message: {e}")
        
    # Callbackga javob qaytarish
    await callback.answer(leader_answer)