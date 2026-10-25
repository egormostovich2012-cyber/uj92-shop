import asyncio
import html
import json
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from aiohttp import web

BOT_TOKEN = "8960664106:AAEZKPLMdPSE_hp044AR5baQrwT0RQo_wtQ"
ADMIN_ID = 6189216877
WEB_APP_URL = "https://egormostovich2012-cyber.github.io/uj92-shop/"
ADMIN_USERNAME = "uj_92"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Команда /start
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Открыть UJ92_shop",
                    web_app=WebAppInfo(url=WEB_APP_URL),
                )
            ]
        ],
        resize_keyboard=True,
    )
    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚡ Запустить магазин",
                    web_app=WebAppInfo(url=WEB_APP_URL),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Отзывы", url="https://t.me/uj_92_rew"
                )
            ],
        ]
    )
    first_name = html.escape(message.from_user.first_name or "клиент")
    text = (
        f"👋 Привет, {first_name}!\n\n"
        f"Добро пожаловать в магазин аккаунтов <b>UJ92_shop</b>.\n"
        f"Здесь вы можете приобрести номера США (+1), Бангладеш (+880), "
        f"Индии (+91) и Британии (+44) с оплатой в GRAM или USDT (TON).\n\n"
        f"Для заказа нажмите кнопку ниже:"
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await message.answer("Перейти к каталогу:", reply_markup=inline_kb)


# Получение заказа после клика «Я ОПЛАТИЛ»
@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    raw_data = message.web_app_data.data
    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError:
        data = {"raw": raw_data}

    country = html.escape(str(data.get("country", "Не указано")))
    code = html.escape(str(data.get("code", "")))
    buyer_user = html.escape(
        str(
            data.get(
                "buyer_username", f"@{message.from_user.username or 'не указан'}"
            )
        )
    )
    currency = html.escape(str(data.get("currency", "USDT")))
    price_val = html.escape(str(data.get("price_val", "0")))
    promo = html.escape(str(data.get("promo", "Не применялся")))
    wallet = html.escape(
        str(
            data.get(
                "wallet", "UQBsw7n4ld0lUPutU8HkmuM6ifGHB3YRxYCGQeQlaAtX6F1Y"
            )
        )
    )

    admin_report = (
        f"🚨 <b>НОВАЯ ЗАЯВКА НА ПОКУПКУ!</b>\n\n"
        f"• <b>Товар:</b> Номер {country} ({code})\n"
        f"• <b>Покупатель (ввел в поле):</b> {buyer_user}\n"
        f"• <b>Telegram покупателя:</b> @{message.from_user.username or 'скрыт'} (ID: <code>{message.from_user.id}</code>)\n"
        f"• <b>Сумма:</b> {price_val} ({currency})\n"
        f"• <b>Промокод:</b> {promo}\n"
        f"• <b>Кошелек:</b> <code>{wallet}</code>\n\n"
        f"<i>Покупатель нажал кнопку «Я оплатил». Проверьте транзакцию в кошельке.</i>"
    )

    buyer_link = (
        f"https://t.me/{message.from_user.username}"
        if message.from_user.username
        else f"tg://user?id={message.from_user.id}"
    )
    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать покупателю", url=buyer_link)]
        ]
    )

    await bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_report,
        parse_mode="HTML",
        reply_markup=admin_kb,
    )

    confirm_text = (
        f"✅ <b>Заявка принята в обработку!</b>\n\n"
        f"Вы выбрали: <b>{country} ({code})</b>\n"
        f"Ваш юзернейм: <b>{buyer_user}</b>\n\n"
        f"Администратор @{ADMIN_USERNAME} проверяет оплату и свяжется с вами."
    )
    await message.answer(confirm_text, parse_mode="HTML")


# Ответ для проверки Render и UptimeRobot
async def handle_ping(request):
    return web.Response(text="UJ92 Shop Bot is alive!")


async def main():
    # 1. Открываем порт для Render
    port = int(os.environ.get("PORT", 10000))
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Веб-порт {port} успешно открыт для Render.")

    # 2. Запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
