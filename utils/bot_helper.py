from config import CHANNEL_USERNAME 

async def is_member(bot, user_id: int, channel: str = CHANNEL_USERNAME) -> bool:
    try:
        member = await bot.get_chat_member(channel, user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        print(f"❌ get_chat_member error: {e}")
        return False
