from aiogram import Router, types, F
from config import ADMIN_USERNAME

router = Router()

@router.message(F.text.contains("Adminga murojaat"))
async def contact_admin(message: types.Message):
    await message.answer(f"📞 Admin bilan bog‘laning: @{ADMIN_USERNAME}")
