from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import API_TOKEN, WEBHOOK_PATH, WEBHOOK_SECRET, WEBHOOK_URL, WEBAPP_HOST, WEBAPP_PORT
from database import get_db_pool, init_db 
from utils.phone_gate import PhoneGateMiddleware

from handlers import (
    start_router,
    promo_router,
    referral_router,
    daily_bonus_router,
    stats_router,
    withdraw_router,
    rating_router,   # user/fake reyting
    admin_broadcast_router,
    admin_ads_router,
    admin_bonus_router,
)

# Fallback router (Router bo'lishi shart!)
fallback_router = Router()

@fallback_router.message()
async def unknown_command(message: types.Message):
    if message.chat.type != "private":
        return
    await message.answer("Noto‘g‘ri buyruq yoki tugma. Menyudan foydalaning yoki qaytadan /start bosing.")

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

phone_gate = PhoneGateMiddleware()
dp.message.middleware(phone_gate)
dp.callback_query.middleware(phone_gate)

dp.include_router(start_router)
dp.include_router(promo_router)
dp.include_router(referral_router)
dp.include_router(daily_bonus_router)
dp.include_router(stats_router)
dp.include_router(withdraw_router)
dp.include_router(rating_router)        # user/fake reyting (bosh menyu)
dp.include_router(admin_broadcast_router) 
dp.include_router(admin_ads_router)
dp.include_router(admin_bonus_router)
dp.include_router(fallback_router)      # fallback oxiriga

async def main():
    app = web.Application()

    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    async def on_startup(_app: web.Application):
        print("🤖 TezRef bot webhook rejimida ishga tushmoqda...")
        pool = await get_db_pool()
        await init_db(pool)
        await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
        print(f"✅ Webhook o'rnatildi: {WEBHOOK_URL}")

    async def on_shutdown(_app: web.Application):
        await bot.delete_webhook(drop_pending_updates=False)
        await bot.session.close()

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=WEBAPP_HOST, port=WEBAPP_PORT)
    await site.start()
    print(f"🌐 Web server ishga tushdi: {WEBAPP_HOST}:{WEBAPP_PORT}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())