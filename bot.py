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

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🛍️ Открыть UJ92_shop",
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
                    text="⚡ Запустить приложение",
                    web_app=WebAppInfo(url=WEB_APP_URL),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Отзывы", url="https://t.me/uj_92_rew"
                ),
                InlineKeyboardButton(
                    text="💬 Поддержка @uj_92",
                    url=f"https://t.me/{ADMIN_USERNAME}",
                ),
            ],
        ]
    )
    first_name = html.escape(message.from_user.first_name or "клиент")
    text = (
        f"👋 Привет, <b>{first_name}</b>!\n\n"
        f"Добро пожаловать в <b>UJ92_shop</b> — магазин аккаунтов Telegram.\n"
        f"• Выбирайте нужное количество номеров в корзине\n"
        f"• Оплачивайте по прямому счёту в GRAM или USDT (TON)\n"
        f"• Отслеживайте статус заказа в разделе «Аккаунт»\n\n"
        f"По всем вопросам и поддержке: @{ADMIN_USERNAME}"
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await message.answer("Нажмите кнопку ниже для входа:", reply_markup=inline_kb)


# Реальная проверка события оплаты (Jetton GRAM/USDT или TON) через TonAPI
async def monitor_order_payment(order_id, chat_id, buyer_tag, amount_str, items_text):
    url = f"https://tonapi.io/v2/accounts/{STORE_WALLET}/events?limit=25"

    for _ in range(20):
        await asyncio.sleep(8)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for ev in data.get("events", []):
                            for act in ev.get("actions", []):
                                j_com = act.get("JettonTransfer", {}).get("comment", "")
                                t_com = act.get("TonTransfer", {}).get("comment", "")
                                if order_id in j_com or order_id in t_com:
                                    # Найдена реальная оплата в блокчейне!
                                    buyer_ok = (
                                        f"✅ <b>Оплата по заказу № {order_id} подтверждена!</b>\n\n"
                                        f"• Сумма: <b>{amount_str}</b>\n"
                                        f"• Заказ:\n{items_text}\n\n"
                                        f"Администратор @{ADMIN_USERNAME} уже уведомлён и свяжется с вами для выдачи номера."
                                    )
                                    await bot.send_message(chat_id=chat_id, text=buyer_ok, parse_mode="HTML")

                                    admin_ok = (
                                        f"💰 <b>ПОДТВЕРЖДЕНА ОПЛАТА В БЛОКЧЕЙНЕ!</b>\n\n"
                                        f"• Счёт: <code>{order_id}</code>\n"
                                        f"• Покупатель: {buyer_tag} (ID: <code>{chat_id}</code>)\n"
                                        f"• Получено: <b>{amount_str}</b>\n"
                                        f"• Товары:\n{items_text}\n\n"
                                        f"<b>Выдайте номер покупателю!</b>"
                                    )
                                    await bot.send_message(chat_id=ADMIN_ID, text=admin_ok, parse_mode="HTML")
                                    return
        except Exception as e:
            logging.warning(f"Ошибка проверки блокчейна: {e}")

    # Если оплата не найдена — честно пишем об ошибке и даём контакт @uj_92
    err_msg = (
        f"⚠️ <b>Заказ № {order_id}: оплата не обнаружена</b>\n\n"
        f"Транзакция с комментарием <code>{order_id}</code> не найдена в сети TON.\n"
        f"Если произошла ошибка или вы уже отправили средства — обратитесь в поддержку: @{ADMIN_USERNAME}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💬 Написать в поддержку @uj_92", url=f"https://t.me/{ADMIN_USERNAME}")]]
    )
    await bot.send_message(chat_id=chat_id, text=err_msg, parse_mode="HTML", reply_markup=kb)


@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
    except Exception:
        return

    order_id = html.escape(str(data.get("id", "UJ92-0000")))
    currency = html.escape(str(data.get("currency", "GRAM")))
    crypto_amt = html.escape(str(data.get("cryptoAmount", "0")))
    usd_amt = html.escape(str(data.get("usdAmount", "0")))
    items = data.get("items", [])

    items_lines = [
        f"  • {i.get('flag', '')} {i.get('country', '')} ({i.get('code', '')}) × {i.get('qty', 1)} шт."
        for i in items
    ]
    items_text = "\n".join(items_lines) if items_lines else "  • Аккаунт Telegram"
    buyer_tag = f"@{message.from_user.username}" if message.from_user.username else f"ID {message.from_user.id}"
    amount_str = f"{crypto_amt} {currency} (${usd_amt})"

    asyncio.create_task(
        monitor_order_payment(
            order_id=order_id,
            chat_id=message.from_user.id,
            buyer_tag=buyer_tag,
            amount_str=amount_str,
            items_text=items_text,
        )
    )


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
    logging.info(f"Веб-порт {port} открыт.")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
