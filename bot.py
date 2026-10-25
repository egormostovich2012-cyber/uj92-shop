import asyncio
import html
import json
import logging
import os
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

BOT_TOKEN = "8960664106:AAEZKPLMdPSE_hp044AR5baQrwT0RQo_wtQ"
ADMIN_ID = 6189216877
WEB_APP_URL = "https://uj-92-shop.github.io/uj92-shop/"
ADMIN_USERNAME = "uj_92"
STORE_WALLET = "UQBsw7n4ld0lUPutU8HkmuM6ifGHB3YRxYCGQeQlaAtX6F1Y"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# /start
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
        f"Номера США (+1), Бангладеш (+880), Индии (+91) и Британии (+44) "
        f"с прямой оплатой через Tonkeeper (сеть TON).\n\n"
        f"Каждый перевод проверяется автоматически в блокчейне."
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await message.answer("Перейти к каталогу:", reply_markup=inline_kb)


# Фоновый сканер блокчейна TON для конкретного заказа
async def monitor_blockchain_for_order(order_code, chat_id, buyer_user, country, code, price_val):
    logging.info(f"Начат поиск транзакции с кодом {order_code} в блокчейне...")
    url = f"https://tonapi.io/v2/blockchain/accounts/{STORE_WALLET}/transactions?limit=15"
    
    # 25 попыток по 7 секунд (~3 минуты ожидания подтверждения сети)
    for attempt in range(25):
        await asyncio.sleep(7)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        txs = data.get("transactions", [])
                        for tx in txs:
                            in_msg = tx.get("in_msg", {})
                            
                            # Проверяем расшифрованный текст комментария в транзакции
                            comment = in_msg.get("decoded_body", {}).get("text", "")
                            
                            if order_code in comment:
                                tx_hash = tx.get("hash", "")
                                tx_url = f"https://tonviewer.com/transaction/{tx_hash}"
                                logging.info(f"Транзакция найдена! Hash: {tx_hash}")

                                # 1. Оповещаем покупателя
                                success_buyer_text = (
                                    f"✅ <b>Оплата подтверждена сетью TON!</b>\n\n"
                                    f"• Заказ: <b>#{order_code}</b>\n"
                                    f"• Товар: <b>{country} ({code})</b>\n\n"
                                    f"Администратор @{ADMIN_USERNAME} уже получил подтверждение и свяжется с вами для выдачи данных."
                                )
                                await bot.send_message(chat_id=chat_id, text=success_buyer_text, parse_mode="HTML")

                                # 2. Оповещаем администратора
                                admin_success_text = (
                                    f"💰 <b>ТРАНЗАКЦИЯ ПОДТВЕРЖДЕНА В БЛОКЧЕЙНЕ!</b>\n\n"
                                    f"• Код заказа: <b>#{order_code}</b>\n"
                                    f"• Товар: Номер {country} ({code})\n"
                                    f"• Покупатель: {buyer_user}\n"
                                    f"• Сумма: {price_val}\n"
                                    f"• Транзакция: <a href='{tx_url}'>Посмотреть в TonViewer</a>\n\n"
                                    f"<b>Можно выдавать товар покупателю!</b>"
                                )
                                admin_kb = InlineKeyboardMarkup(
                                    inline_keyboard=[[InlineKeyboardButton(text="💬 Написать клиенту", url=f"tg://user?id={chat_id}")]]
                                )
                                await bot.send_message(chat_id=ADMIN_ID, text=admin_success_text, parse_mode="HTML", reply_markup=admin_kb)
                                return

        except Exception as e:
            logging.warn(f"Ошибка при запросе к блокчейн API: {e}")

    # Если за 3 минуты блокчейн не вернул транзакцию
    timeout_text = (
        f"⏳ <b>Транзакция #{order_code} пока обрабатывается валидаторами.</b>\n"
        f"Если вы подтвердили перевод в кошельке, администратор @{ADMIN_USERNAME} проверит её вручную."
    )
    await bot.send_message(chat_id=chat_id, text=timeout_text, parse_mode="HTML")


# Получение заявки из Mini App после нажатия «Оплатить»
@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    raw_data = message.web_app_data.data
    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError:
        data = {"raw": raw_data}

    order_code = html.escape(str(data.get("order_code", "UJ-000000")))
    country = html.escape(str(data.get("country", "Не указано")))
    code = html.escape(str(data.get("code", "")))
    buyer_user = html.escape(str(data.get("buyer_username", f"@{message.from_user.username or 'не указан'}")))
    price_val = html.escape(str(data.get("price_val", "0")))

    # 1. Отвечаем покупателю о начале блокчейн-проверки
    user_wait_text = (
        f"⏳ <b>Заказ #{order_code} принят в обработку!</b>\n\n"
        f"• Товар: <b>{country} ({code})</b>\n"
        f"• Сумма: <b>{price_val}</b>\n"
        f"• Код в комментарии: <code>{order_code}</code>\n\n"
        f"<i>Ищу транзакцию в блокчейне TON... Обычно это занимает от 10 до 40 секунд.</i>"
    )
    await message.answer(user_wait_text, parse_mode="HTML")

    # 2. Уведомляем администратора о создании заказа
    admin_notify_text = (
        f"🚨 <b>НОВЫЙ ЗАКАЗ #{order_code}</b>\n\n"
        f"• Товар: Номер {country} ({code})\n"
        f"• Покупатель: {buyer_user} (ID: <code>{message.from_user.id}</code>)\n"
        f"• Сумма: {price_val}\n"
        f"• Ожидаемый комментарий: <code>{order_code}</code>\n\n"
        f"<i>Бот начал поиск транзакции в блокчейне...</i>"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=admin_notify_text, parse_mode="HTML")

    # 3. Запускаем параллельную проверку сети TON
    asyncio.create_task(
        monitor_blockchain_for_order(
            order_code=order_code,
            chat_id=message.from_user.id,
            buyer_user=buyer_user,
            country=country,
            code=code,
            price_val=price_val
        )
    )


# Веб-сервер для удержания процесса на Render
async def handle_ping(request):
    return web.Response(text="UJ92 Shop Bot is alive!")


async def main():
    port = int(os.environ.get("PORT", 10000))
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Веб-порт {port} открыт для Render.")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
