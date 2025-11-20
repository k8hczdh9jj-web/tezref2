from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

from config import API_TOKEN
from database import get_db_pool, init_db 

from handlers import (
    start_router,
    promo_router,
    referral_router,
    stats_router,
    withdraw_router,
    contact_admin_router,
    rating_router,   # user/fake reyting
    team_router,      # team reyting
    admin_broadcast_router
)

# Fallback router (Router bo'lishi shart!)
fallback_router = Router()

@fallback_router.message()
async def unknown_command(message: types.Message):
    await message.answer("Noto‘g‘ri buyruq yoki tugma. Menyudan foydalaning yoki qaytadan /start bosing.")

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

dp.include_router(start_router)
dp.include_router(promo_router)
dp.include_router(referral_router)
dp.include_router(stats_router)
dp.include_router(withdraw_router)
dp.include_router(rating_router)        # user/fake reyting (bosh menyu)
dp.include_router(team_router)          # team reyting (team menyusi)
dp.include_router(contact_admin_router)
dp.include_router(admin_broadcast_router) 
dp.include_router(fallback_router)      # fallback oxiriga

async def main():
    print("🤖 TezRef bot ishga tushdi...")
    pool = await get_db_pool()
    await init_db(pool)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())