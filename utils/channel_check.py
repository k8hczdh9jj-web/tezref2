from aiogram import Bot
from config import CHANNEL_USERNAME, CHANNEL_USERNAME_2 

async def is_member_channel_1(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)  # to'liq username
        return member.status in ['creator', 'administrator', 'member']
    except:
        return False

async def is_member_channel_2(bot: Bot, user_id: int) -> bool:
    """Promokod olish uchun kanalga a'zo ekanligini tekshirish"""
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME_2.replace('@', ''), user_id)
        return member.status in ['creator', 'administrator', 'member']
    except:
        return False
