from aiogram import Bot
from config import REQUIRED_CHANNEL_ID

async def is_member_required_channel(bot: Bot, user_id: int) -> bool:
    """Majburiy kanalga a'zo ekanligini tekshirish."""
    if not REQUIRED_CHANNEL_ID:
        return False

    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        return member.status in ['creator', 'administrator', 'member']
    except:
        return False