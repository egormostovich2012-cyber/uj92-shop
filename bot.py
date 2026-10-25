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
ADMIN_USERNAME = "uj_92"
WEB_APP_URL = "https://uj-92-shop.github.io/uj92-shop/"
STORE_WALLET = "UQBsw7n4ld0lUPutU8HkmuM6ifGHB3YRxYCGQeQlaAtX6F1Y"

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
        f"Индии (+91) и Британии (+44) с прямой оплатой в сети TON.\n\n"
        f"Нажмите кнопку ниже, чтобы открыть каталог:"
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await message.answer("Перейти к каталогу:", reply_markup=inline_kb)


# Фоновый сканер сети TON
async def monitor_blockchain_for_order(order_code, chat_id, buyer_user, country, code, price_val, currency):
    logging.info(f"Начат поиск транзакции #{order_code} в блокчейне...")
    url = f"https://tonapi.io/v2/blockchain/accounts/{STORE_WALLET}/transactions?limit=20"
    
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
                            comment = in_msg.get("decoded_body", {}).get("text", "")
                            
                            # Проверяем уникальный код чека в комментарии
                            if order_code in comment:
                                tx_hash = tx.get("hash", "")
                                tx_url = f"https://tonviewer.com/transaction/{tx_hash}"

                                # 1. Уведомление покупателю
                                buyer_text = (
                                    f"✅ <b>ОПЛАТА ПОДТВЕРЖДЕНА В СЕТИ TON!</b>\n\n"
                                    f"• Код чека: <b>#{order_code}</b>\n"
                                    f"• Товар: <b>Номер {country} ({code})</b>\n"
                                    f"• Сумма: <b>{price_val} {currency}</b>\n\n"
                                    f"Администратор @{ADMIN_USERNAME} получил уведомление и свяжется с вами для передачи кода авторизации."
                                )
                                buyer_kb = InlineKeyboardMarkup(
                                    inline_keyboard=[[InlineKeyboardButton(text="💬 Написать админу", url=f"https://t.me/{ADMIN_USERNAME}")]]
                                )
                                await bot.send_message(chat_id=chat_id, text=buyer_text, parse_mode="HTML", reply_markup=buyer_kb)

                                # 2. Уведомление администратору (6189216877)
                                admin_confirmed_text = (
                                    f"💰 <b>ТРАНЗАКЦИЯ ПОДТВЕРЖДЕНА В СЕТИ TON!</b>\n\n"
                                    f"• Код чека: <b>#{order_code}</b>\n"
                                    f"• Товар: <b>Номер {country} ({code})</b>\n"
                                    f"• Покупатель: {buyer_user} (ID: <code>{chat_id}</code>)\n"
                                    f"• Получено: <b>{price_val} {currency}</b>\n"
                                    f"• Транзакция: <a href='{tx_url}'>Смотреть в TonViewer</a>\n\n"
                                    f"<b>Выдайте покупателю номер и код подтверждения!</b>"
                                )
                                admin_kb = InlineKeyboardMarkup(
                                    inline_keyboard=[[InlineKeyboardButton(text="💬 Написать клиенту", url=f"tg://user?id={chat_id}")]]
                                )
                                await bot.send_message(chat_id=ADMIN_ID, text=admin_confirmed_text, parse_mode="HTML", reply_markup=admin_kb)
                                return
        except Exception as e:
            logging.warning(f"Ошибка проверки блокчейна: {e}")

    # Если автоматический поиск истек по таймауту
    timeout_text = (
        f"⏳ <b>Транзакция по чеку #{order_code} в обработке.</b>\n\n"
        f"Если средства уже списались с кошелька, напишите напрямую администратору @{ADMIN_USERNAME} для ускорения выдачи."
    )
    await bot.send_message(chat_id=chat_id, text=timeout_text, parse_mode="HTML")


# Получение данных чека из Mini App
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
    currency = html.escape(str(data.get("currency", "USDT")))
    price_val = html.escape(str(data.get("price_val", "0")))

    # 1. Ответ покупателю с четкой последовательностью
    buyer_order_text = (
        f"🧾 <b>ЭЛЕКТРОННЫЙ ЧЕК ЗАКАЗА #{order_code}</b>\n\n"
        f"• <b>Товар:</b> Номер {country} ({code})\n"
        f"• <b>Сумма:</b> {price_val}\n"
        f"• <b>Сеть:</b> The Open Network (TON)\n\n"
        f"<b>Последовательность выполнения:</b>\n"
        f"1️⃣ <b>Заказ создан:</b> ✅ Выполнено\n"
        f"2️⃣ <b>Проверка оплаты:</b> 🔄 Ожидаем подтверждения сети TON...\n"
        f"3️⃣ <b>Выдача номера:</b> ⏳ В очереди (выдаёт @{ADMIN_USERNAME})"
    )
    await message.answer(buyer_order_text, parse_mode="HTML")

    # 2. МГНОВЕННОЕ УВЕДОМЛЕНИЕ АДМИНИСТРАТОРУ @uj_92 (6189216877)
    admin_alert_text = (
        f"🚨 <b>НОВЫЙ ЗАКАЗ В МАГАЗИНЕ!</b>\n\n"
        f"• <b>Чек заказа:</b> <code>#{order_code}</code>\n"
        f"• <b>Товар:</b> Номер {country} ({code})\n"
        f"• <b>Покупатель:</b> {buyer_user}\n"
        f"• <b>Telegram ID:</b> <code>{message.from_user.id}</code>\n"
        f"• <b>Сумма к получению:</b> <b>{price_val}</b>\n"
        f"• <b>Комментарий для сверки:</b> <code>{order_code}</code>\n\n"
        f"<i>Бот начал проверку транзакции в блокчейне...</i>"
    )
    buyer_direct_link = (
        f"https://t.me/{message.from_user.username}"
        if message.from_user.username
        else f"tg://user?id={message.from_user.id}"
    )
    admin_btn = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💬 Открыть диалог с покупателем", url=buyer_direct_link)]]
    )
    await bot.send_message(chat_id=ADMIN_ID, text=admin_alert_text, parse_mode="HTML", reply_markup=admin_btn)

    # 3. Запуск фоновой проверки блокчейна
    asyncio.create_task(
        monitor_blockchain_for_order(
            order_code=order_code,
            chat_id=message.from_user.id,
            buyer_user=buyer_user,
            country=country,
            code=code,
            price_val=price_val,
            currency=currency
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
