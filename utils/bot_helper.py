from config import REQUIRED_CHANNEL_ID

async def is_member(bot, user_id: int, channel: int | None = None) -> bool:
    target_channel = channel or REQUIRED_CHANNEL_ID
    if not target_channel:
        return False

    try:
        member = await bot.get_chat_member(target_channel, user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        print(f"❌ get_chat_member error: {e}")
        return False
