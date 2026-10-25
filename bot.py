import asyncio
import html
import json
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

# --- ВАШИ НАСТРОЙКИ ---
BOT_TOKEN = "8960664106:AAEZKPLMdPSE_hp044AR5baQrwT0RQo_wtQ"
ADMIN_ID = 6189216877
WEB_APP_URL = "https://egormostovich2012-cyber.github.io/uj92-shop/"
ADMIN_USERNAME = "uj_92"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Обработка команды /start
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    # Кнопка под полем ввода клавиатуры
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

    # Инлайн-кнопки прямо под сообщением
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


# Обработка данных после клика «Я ОПЛАТИЛ»
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
    price_usd = html.escape(str(data.get("price_usd", "0")))
    currency = html.escape(str(data.get("currency", "USDT")))
    price_val = html.escape(str(data.get("price_val", price_usd)))
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
        f"• <b>Сумма к оплате:</b> {price_val} ({currency})\n"
        f"• <b>Промокод:</b> {promo}\n"
        f"• <b>Кошелек оплаты:</b> <code>{wallet}</code>\n\n"
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

    # 1. Отправка отчета администратору
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_report,
        parse_mode="HTML",
        reply_markup=admin_kb,
    )

    # 2. Подтверждение покупателю
    confirm_text = (
        f"✅ <b>Заявка принята в обработку!</b>\n\n"
        f"Вы выбрали: <b>{country} ({code})</b>\n"
        f"Ваш юзернейм: <b>{buyer_user}</b>\n\n"
        f"Администратор @{ADMIN_USERNAME} проверяет оплату и свяжется с вами."
    )
    await message.answer(confirm_text, parse_mode="HTML")


async def main():
    print("Бот UJ92_shop успешно запущен и слушает события...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())