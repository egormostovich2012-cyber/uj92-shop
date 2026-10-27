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

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8960664106:AAEZKPLMdPSE_hp044AR5baQrwT0RQo_wtQ"
ADMIN_ID = 6189216877
ADMIN_USERNAME = "uj_92"
WEB_APP_URL = "https://uj-92-shop.github.io/uj92-shop/"
STORE_WALLET = "UQBsw7n4ld0lUPutU8HkmuM6ifGHB3YRxYCGQeQlaAtX6F1Y"

COUNTRIES_MAP = {
    "us": "Америка (+1)",
    "bd": "Бангладеш (+880)",
    "in": "Индия (+91)",
    "gb": "Британия (+44)",
}

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
            [
                InlineKeyboardButton(
                    text="💬 Поддержка", url=f"https://t.me/{ADMIN_USERNAME}"
                )
            ],
        ]
    )
    first_name = html.escape(message.from_user.first_name or "клиент")
    text = (
        f"👋 Привет, {first_name}!\n\n"
        f"Добро пожаловать в магазин аккаунтов <b>UJ92_shop</b>.\n"
        f"Для заказа выберите нужное количество номеров в каталоге и оплатите счёт в сети TON.\n\n"
        f"<i>При возникновении вопросов: @{ADMIN_USERNAME}</i>"
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await message.answer("Перейти к покупкам:", reply_markup=inline_kb)


# Фоновый сканер сети TON (проверка по уникальному коду заказа)
async def monitor_blockchain_for_order(
    order_code, chat_id, buyer_user, total_sum, items_text
):
    logging.info(f"Сканирование блокчейна TON для заказа #{order_code}...")
    url = f"https://tonapi.io/v2/blockchain/accounts/{STORE_WALLET}/transactions?limit=20"

    for attempt in range(25):  # 25 проверок по 7 секунд (~3 минуты)
        await asyncio.sleep(7)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        txs = data.get("transactions", [])
                        for tx in txs:
                            in_msg = tx.get("in_msg", {})
                            comment = (
                                in_msg.get("decoded_body", {}).get("text", "")
                            )

                            if order_code in comment:
                                tx_hash = tx.get("hash", "")
                                tx_url = (
                                    f"https://tonviewer.com/transaction/{tx_hash}"
                                )

                                # 1. Уведомление покупателю
                                buyer_done = (
                                    f"✅ <b>ОПЛАТА ПОЛУЧЕНА И ПОДТВЕРЖДЕНА В СЕТИ TON!</b>\n\n"
                                    f"• Номер счёта: <b>#{order_code}</b>\n"
                                    f"• Сумма: <b>{total_sum}</b>\n\n"
                                    f"Администратор @{ADMIN_USERNAME} получил уведомление и свяжется с вами для выдачи кода авторизации."
                                )
                                buyer_kb = InlineKeyboardMarkup(
                                    inline_keyboard=[
                                        [
                                            InlineKeyboardButton(
                                                text="💬 Написать админу",
                                                url=f"https://t.me/{ADMIN_USERNAME}",
                                            )
                                        ]
                                    ]
                                )
                                await bot.send_message(
                                    chat_id=chat_id,
                                    text=buyer_done,
                                    parse_mode="HTML",
                                    reply_markup=buyer_kb,
                                )

                                # 2. Уведомление администратору (@uj_92 / 6189216877)
                                admin_confirmed = (
                                    f"💰 <b>ТРАНЗАКЦИЯ ПОДТВЕРЖДЕНА В БЛОКЧЕЙНЕ!</b>\n\n"
                                    f"• Счёт: <b>#{order_code}</b>\n"
                                    f"• Клиент: {buyer_user} (ID: <code>{chat_id}</code>)\n"
                                    f"• Товары:\n{items_text}\n"
                                    f"• Сумма: <b>{total_sum}</b>\n"
                                    f"• Ссылка на сеть: <a href='{tx_url}'>TonViewer</a>\n\n"
                                    f"<b>Выдайте покупателю номер и код!</b>"
                                )
                                admin_kb = InlineKeyboardMarkup(
                                    inline_keyboard=[
                                        [
                                            InlineKeyboardButton(
                                                text="💬 Написать клиенту",
                                                url=f"tg://user?id={chat_id}",
                                            )
                                        ]
                                    ]
                                )
                                await bot.send_message(
                                    chat_id=ADMIN_ID,
                                    text=admin_confirmed,
                                    parse_mode="HTML",
                                    reply_markup=admin_kb,
                                )
                                return
        except Exception as e:
            logging.warning(f"Ошибка проверки TonAPI: {e}")

    # Честное сообщение, если за 3 минуты блокчейн не вернул транзакцию
    timeout_msg = (
        f"⏳ <b>Счёт #{order_code}</b>\n\n"
        f"Транзакция пока не обнаружена в блокчейне TON.\n"
        f"Если средства уже списались с кошелька, обратитесь в поддержку к администратору @{ADMIN_USERNAME}."
    )
    await bot.send_message(chat_id=chat_id, text=timeout_msg, parse_mode="HTML")


# Обработка сформированного счёта из Mini App
@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    raw_data = message.web_app_data.data
    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError:
        data = {"raw": raw_data}

    order_code = html.escape(str(data.get("order_code", "UJ-000000")))
    buyer_user = html.escape(
        str(
            data.get(
                "buyer_username", f"@{message.from_user.username or 'не указан'}"
            )
        )
    )
    total_sum = html.escape(str(data.get("total_sum", "0")))
    raw_items = data.get("items", {})

    # Формируем читаемый список товаров
    items_lines = []
    if isinstance(raw_items, dict):
        for pid, qty in raw_items.items():
            name = COUNTRIES_MAP.get(pid, pid)
            items_lines.append(f"  — {name}: {qty} шт.")
    items_text = "\n".join(items_lines) if items_lines else "  — Номера"

    # 1. Дублируем информацию о счёте покупателю в чат
    buyer_msg = (
        f"🧾 <b>СЧЁТ НА ОПЛАТУ #{order_code} СФОРМИРОВАН</b>\n\n"
        f"<b>Состав заказа:</b>\n{items_text}\n\n"
        f"• <b>Сумма к оплате:</b> {total_sum}\n"
        f"• <b>Сеть:</b> The Open Network (TON)\n"
        f"• <b>Кошелек:</b> <code>{STORE_WALLET}</code>\n"
        f"• <b>Комментарий:</b> <code>{order_code}</code>\n\n"
        f"<b>Этапы выполнения:</b>\n"
        f"1️⃣ <b>Счёт выставлен:</b> ✅ Выполнено\n"
        f"2️⃣ <b>Проверка блокчейна:</b> 🔄 Ожидаем перевод...\n"
        f"3️⃣ <b>Выдача номеров:</b> ⏳ Ожидает связи с @{ADMIN_USERNAME}\n\n"
        f"<i>Если у вас возникли сложности с оплатой, напишите в поддержку: @{ADMIN_USERNAME}</i>"
    )
    await message.answer(buyer_msg, parse_mode="HTML")

    # 2. ОБЯЗАТЕЛЬНОЕ УВЕДОМЛЕНИЕ АДМИНИСТРАТОРУ @uj_92 (ID 6189216877)
    admin_alert = (
        f"🚨 <b>НОВЫЙ ЗАКАЗ В МАГАЗИНЕ!</b>\n\n"
        f"• <b>Номер счёта:</b> <code>#{order_code}</code>\n"
        f"• <b>Покупатель:</b> {buyer_user} (ID: <code>{message.from_user.id}</code>)\n"
        f"• <b>Товары:</b>\n{items_text}\n"
        f"• <b>Сумма:</b> <b>{total_sum}</b>\n"
        f"• <b>Комментарий для сверки:</b> <code>{order_code}</code>\n\n"
        f"<i>Бот запустил сканирование блокчейна на поступление средств.</i>"
    )
    buyer_chat_link = (
        f"https://t.me/{message.from_user.username}"
        if message.from_user.username
        else f"tg://user?id={message.from_user.id}"
    )
    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Написать покупателю", url=buyer_chat_link
                )
            ]
        ]
    )
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_alert,
        parse_mode="HTML",
        reply_markup=admin_kb,
    )

    # 3. Запуск фоновой проверки
    asyncio.create_task(
        monitor_blockchain_for_order(
            order_code=order_code,
            chat_id=message.from_user.id,
            buyer_user=buyer_user,
            total_sum=total_sum,
            items_text=items_text,
        )
    )


# Веб-сервер Render
async def handle_ping(request):
    return web.Response(text="UJ92 Shop Bot is running!")


async def main():
    port = int(os.environ.get("PORT", 10000))
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Порт {port} открыт.")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
