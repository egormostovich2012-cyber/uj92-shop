import asyncio
import html
import logging
import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from aiohttp import web

logging.basicConfig(level=logging.INFO)

raw_token = os.environ.get("BOT_TOKEN", "")
BOT_TOKEN = raw_token.strip().strip('"').strip("'")

if not BOT_TOKEN or ":" not in BOT_TOKEN:
    logging.error(
        "ОШИБКА: Переменная BOT_TOKEN не задана в Environment на Render!"
    )
    sys.exit(1)

ADMIN_ID = 6189216877
ADMIN_USERNAME = "uj_92"
WEB_APP_URL = "https://uj-92-shop.github.io/uj92-shop/"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


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
        f"Добро пожаловать в <b>UJ92_shop</b> — магазин номеров и кейсов с подарками Telegram.\n"
        f"• Пополняйте баланс в GRAM или USDT (TON)\n"
        f"• Открывайте кейс «Бомж» и собирайте подарки в инвентарь\n"
        f"• Покупайте номера с мгновенным отслеживанием статуса\n\n"
        f"Поддержка: @{ADMIN_USERNAME}"
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await message.answer("Нажмите кнопку ниже для входа:", reply_markup=inline_kb)


async def handle_api_notify(request):
    if request.method == "OPTIONS":
        return web.Response(status=200, headers=CORS_HEADERS)

    try:
        body = await request.json()
        order = body.get("order", {})
        user = body.get("user", {})
        event_type = body.get("eventType", "created")

        order_id = html.escape(str(order.get("id", "UJ92")))
        order_type = order.get("orderType", "phone")
        currency = html.escape(str(order.get("currency", "GRAM")))
        crypto_amt = html.escape(str(order.get("cryptoAmount", "0")))
        usd_amt = html.escape(str(order.get("usdAmount", "0")))
        promo = html.escape(str(order.get("promo", "Нет")))
        items = order.get("items", [])

        user_id = user.get("id", 0)
        user_name = html.escape(str(user.get("name", "Клиент")))
        user_tag = html.escape(str(user.get("username", "@guest")))

        items_str = "\n".join(
            [
                f"• {i.get('flag', '')} {i.get('country', '')} ({i.get('code', '')}) × {i.get('qty', 1)} шт."
                for i in items
            ]
        )

        if order_type == "gift_withdraw":
            admin_text = (
                f"🎁 <b>ЗАЯВКА НА ВЫВОД ПОДАРКА ИЗ ИНВЕНТАРЯ!</b>\n\n"
                f"• Код заявки: <code>{order_id}</code>\n"
                f"• Покупатель: {user_name} ({user_tag}, ID: <code>{user_id}</code>)\n"
                f"• Подарок:\n{items_str}\n\n"
                f"<b>Отправьте этот подарок пользователю в Telegram!</b>"
            )
            buyer_text = (
                f"🎁 <b>Заявка № {order_id} на вывод подарка создана!</b>\n\n"
                f"{items_str}\n\n"
                f"Администратор @{ADMIN_USERNAME} уже получил уведомление и отправит подарок на ваш аккаунт."
            )
        elif order_type == "deposit":
            if event_type == "paid":
                admin_text = (
                    f"💰 <b>ПОПОЛНЕНИЕ БАЛАНСА ПОДТВЕРЖДЕНО!</b>\n\n"
                    f"• Счёт: <code>{order_id}</code>\n"
                    f"• Пользователь: {user_name} ({user_tag}, ID: <code>{user_id}</code>)\n"
                    f"• Зачислено: <b>${usd_amt} ({crypto_amt} {currency})</b>"
                )
                buyer_text = (
                    f"✅ <b>Ваш баланс успешно пополнен на ${usd_amt}!</b>\n"
                    f"Счёт № <code>{order_id}</code> подтверждён в блокчейне TON."
                )
            else:
                admin_text = (
                    f"💳 <b>НОВЫЙ СЧЁТ НА ПОПОЛНЕНИЕ БАЛАНСА</b>\n\n"
                    f"• Счёт: <code>{order_id}</code>\n"
                    f"• Пользователь: {user_name} ({user_tag}, ID: <code>{user_id}</code>)\n"
                    f"• Сумма: <b>{crypto_amt} {currency} (${usd_amt})</b>\n"
                    f"• Комментарий: <code>{order_id}</code>"
                )
                buyer_text = (
                    f"🧾 <b>Счёт № {order_id} на пополнение баланса (${usd_amt}) создан!</b>\n\n"
                    f"• К оплате: <b>{crypto_amt} {currency}</b>\n"
                    f"• Комментарий: <code>{order_id}</code>\n\n"
                    f"Подтвердите оплату в Tonkeeper. При возникновении ошибок пишите @{ADMIN_USERNAME}"
                )
        else:
            if event_type == "paid":
                admin_text = (
                    f"💰 <b>ЗАКАЗ ОПЛАЧЕН!</b>\n\n"
                    f"• Заказ: <code>{order_id}</code>\n"
                    f"• Покупатель: {user_name} ({user_tag}, ID: <code>{user_id}</code>)\n"
                    f"• Сумма: <b>{crypto_amt} {currency} (${usd_amt})</b>\n"
                    f"• Товары:\n{items_str}\n\n"
                    f"✅ <b>Выдайте покупателю номер!</b>"
                )
                buyer_text = (
                    f"✅ <b>Оплата по заказу № {order_id} подтверждена!</b>\n\n"
                    f"• Сумма: <b>{crypto_amt} {currency} (${usd_amt})</b>\n"
                    f"• Товары:\n{items_str}\n\n"
                    f"Администратор @{ADMIN_USERNAME} сейчас выдаст вам номер."
                )
            else:
                admin_text = (
                    f"🚨 <b>НОВЫЙ ЗАКАЗ В UJ92_SHOP!</b>\n\n"
                    f"• Номер заказа: <code>{order_id}</code>\n"
                    f"• Покупатель: {user_name} ({user_tag}, ID: <code>{user_id}</code>)\n"
                    f"• Счёт: <b>{crypto_amt} {currency} (${usd_amt})</b>\n"
                    f"• Промокод: {promo}\n"
                    f"• Товары:\n{items_str}\n"
                    f"• Комментарий: <code>{order_id}</code>"
                )
                buyer_text = (
                    f"🧾 <b>Заказ № {order_id} создан!</b>\n\n"
                    f"<b>Состав заказа:</b>\n{items_str}\n\n"
                    f"• <b>Сумма счёта:</b> {crypto_amt} {currency} (${usd_amt})\n"
                    f"• <b>Комментарий:</b> <code>{order_id}</code>\n\n"
                    f"Подтвердите счёт в кошельке. По всем вопросам: @{ADMIN_USERNAME}"
                )

        buyer_url = (
            f"https://t.me/{user_tag[1:]}"
            if user_tag.startswith("@")
            else f"tg://user?id={user_id}"
        )
        admin_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💬 Написать покупателю", url=buyer_url)]
            ]
        )
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            parse_mode="HTML",
            reply_markup=admin_kb,
        )

        if user_id and int(user_id) != 0:
            buyer_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💬 Поддержка @uj_92",
                            url=f"https://t.me/{ADMIN_USERNAME}",
                        )
                    ]
                ]
            )
            await bot.send_message(
                chat_id=int(user_id),
                text=buyer_text,
                parse_mode="HTML",
                reply_markup=buyer_kb,
            )

        return web.json_response({"ok": True}, headers=CORS_HEADERS)
    except Exception as e:
        logging.error(f"Ошибка отправки уведомления: {e}")
        return web.json_response(
            {"ok": False, "error": str(e)}, status=500, headers=CORS_HEADERS
        )


async def handle_ping(request):
    return web.Response(text="UJ92 Shop Bot is alive!", headers=CORS_HEADERS)


async def main():
    port = int(os.environ.get("PORT", 10000))
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_route("OPTIONS", "/notify", handle_api_notify)
    app.router.add_post("/notify", handle_api_notify)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Веб-порт {port} успешно открыт.")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
