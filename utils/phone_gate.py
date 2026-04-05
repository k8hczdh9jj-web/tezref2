from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, types
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from database import get_db_pool


PHONE_REQUIRED_TEXT = "📱 Davom etish uchun telefon raqamingizni ulashing."


def phone_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def has_phone_number(user_id: int) -> bool:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT phone_number FROM users WHERE user_id=$1",
            user_id,
        )

    return bool(row and row["phone_number"])


class PhoneGateMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        if isinstance(event, types.Message):
            if event.chat and event.chat.type in {"group", "supergroup"}:
                return await handler(event, data)

        if isinstance(event, types.CallbackQuery):
            if event.message and event.message.chat and event.message.chat.type in {"group", "supergroup"}:
                return await handler(event, data)

        if isinstance(event, types.Message):
            if event.contact:
                return await handler(event, data)

            text = event.text or ""
            if text.startswith("/start"):
                return await handler(event, data)

        if await has_phone_number(user.id):
            return await handler(event, data)

        if isinstance(event, types.CallbackQuery):
            await event.answer("Avval telefon raqamingizni ulashing.", show_alert=True)
            if event.message:
                await event.message.answer(
                    PHONE_REQUIRED_TEXT,
                    reply_markup=phone_request_keyboard(),
                )
            return None

        if isinstance(event, types.Message):
            await event.answer(
                PHONE_REQUIRED_TEXT,
                reply_markup=phone_request_keyboard(),
            )
            return None

        return await handler(event, data)
