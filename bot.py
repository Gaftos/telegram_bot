import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ===== ВРЕМЕННАЯ "БАЗА ДАННЫХ" (в памяти) =====
users_db = {}

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {
            "balance": 100000.00,
            "loans": [],
            "deposits": [],
            "operations": [],
            "properties": [],
            "qr_code": f"QR{user_id}"
        }
    return users_db[user_id]

# ===== КЛАВИАТУРЫ =====

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="💳 Кредиты")],
            [KeyboardButton(text="📈 Вклады"), KeyboardButton(text="📜 История операций")],
            [KeyboardButton(text="🏠 Недвижимость"), KeyboardButton(text="📷 QR-переводы")],
        ],
        resize_keyboard=True
    )

# ===== ОБРАБОТЧИКИ =====

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = get_user(message.from_user.id)
    await message.answer(
        f"🏦 Добро пожаловать в Банк, {message.from_user.first_name}!\n\n"
        f"Ваш ID: {message.from_user.id}\n"
        f"QR-код для переводов: {user['qr_code']}",
        reply_markup=main_menu()
    )

# ===== БАЛАНС =====

@dp.message(F.text == "💰 Баланс")
async def show_balance(message: Message):
    user = get_user(message.from_user.id)
    
    loans_text = "Нет действующих кредитов"
    if user["loans"]:
        loans_text = "\n".join([f"• {l['type']}: {l['amount']:,} ₽ (ставка {l['rate']}%, {l['months']} мес.)" for l in user["loans"]])
    
    deposits_text = "Нет действующих вкладов"
    if user["deposits"]:
        deposits_text = "\n".join([f"• {d['type']}: {d['amount']:,} ₽ (ставка {d['rate']}%, до {d['end_date']})" for d in user["deposits"]])
    
    await message.answer(
        f"💰 <b>Ваш баланс</b>\n\n"
        f"Доступно: <b>{user['balance']:,.2f} ₽</b>\n\n"
        f"📋 <b>Действующие кредиты:</b>\n{loans_text}\n\n"
        f"📈 <b>Действующие вклады:</b>\n{deposits_text}",
        parse_mode="HTML"
    )

# ===== КРЕДИТЫ =====

@dp.message(F.text == "💳 Кредиты")
async def loans_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 Потребительский кредит", callback_data="loan_consumer")],
        [InlineKeyboardButton(text="🏠 Кредит под залог недвижимости", callback_data="loan_mortgage")],
        [InlineKeyboardButton(text="📋 Мои кредиты", callback_data="loan_my")]
    ])
    await message.answer("Выберите тип кредита:", reply_markup=keyboard)

@dp.callback_query(F.data == "loan_consumer")
async def loan_consumer_info(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🏦 <b>Потребительский кредит</b>\n\n"
        "• Сумма: до 5 000 000 ₽\n"
        "• Ставка: от 12.9% годовых\n"
        "• Срок: до 5 лет\n"
        "• Без залога и поручителей\n\n"
        "Для оформления обратитесь в отделение или нажмите кнопку ниже.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оформить кредит", callback_data="loan_apply_consumer")]
        ])
    )

@dp.callback_query(F.data == "loan_mortgage")
async def loan_mortgage_info(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🏠 <b>Кредит под залог недвижимости</b>\n\n"
        "• Сумма: до 30 000 000 ₽\n"
        "• Ставка: от 9.5% годовых\n"
        "• Срок: до 20 лет\n"
        "• Залог: квартира, дом, земельный участок\n\n"
        "Требуется оценка недвижимости.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подать заявку", callback_data="loan_apply_mortgage")]
        ])
    )

@dp.callback_query(F.data == "loan_my")
async def loan_my(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user["loans"]:
        await callback.message.edit_text("У вас нет действующих кредитов.")
    else:
        text = "📋 <b>Ваши кредиты:</b>\n\n"
        for i, loan in enumerate(user["loans"], 1):
            text += f"{i}. {loan['type']}: {loan['amount']:,.0f} ₽\n   Ставка: {loan['rate']}%, {loan['months']} мес.\n\n"
        await callback.message.edit_text(text, parse_mode="HTML")

@dp.callback_query(F.data.startswith("loan_apply_"))
async def loan_apply(callback: types.CallbackQuery):
    loan_type = "Потребительский" if "consumer" in callback.data else "Под залог недвижимости"
    user = get_user(callback.from_user.id)
    new_loan = {
        "type": loan_type,
        "amount": 500000 if "consumer" in callback.data else 3000000,
        "rate": 12.9 if "consumer" in callback.data else 9.5,
        "months": 36 if "consumer" in callback.data else 120
    }
    user["loans"].append(new_loan)
    user["balance"] += new_loan["amount"]
    user["operations"].append(f"Получен кредит {loan_type}: +{new_loan['amount']:,.0f} ₽")
    await callback.message.edit_text(
        f"✅ Кредит одобрен!\n\n"
        f"Тип: {loan_type}\n"
        f"Сумма: {new_loan['amount']:,.0f} ₽\n"
        f"Ставка: {new_loan['rate']}%\n"
        f"Срок: {new_loan['months']} мес.\n\n"
        f"Средства зачислены на баланс."
    )

# ===== ВКЛАДЫ =====

@dp.message(F.text == "📈 Вклады")
async def deposits_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои вклады", callback_data="deposit_my")],
        [InlineKeyboardButton(text="➕ Открыть новый вклад", callback_data="deposit_new")]
    ])
    await message.answer("Раздел вкладов:", reply_markup=keyboard)

@dp.callback_query(F.data == "deposit_my")
async def deposit_my(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user["deposits"]:
        await callback.message.edit_text("У вас нет действующих вкладов.")
    else:
        text = "📈 <b>Ваши вклады:</b>\n\n"
        for i, dep in enumerate(user["deposits"], 1):
            text += f"{i}. {dep['type']}: {dep['amount']:,.0f} ₽\n   Ставка: {dep['rate']}%, до {dep['end_date']}\n\n"
        await callback.message.edit_text(text, parse_mode="HTML")

@dp.callback_query(F.data == "deposit_new")
async def deposit_new(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Сберегательный (8% годовых)", callback_data="deposit_open_8")],
        [InlineKeyboardButton(text="🏆 Премиум (10% годовых)", callback_data="deposit_open_10")],
        [InlineKeyboardButton(text="📅 Годовой (12% годовых)", callback_data="deposit_open_12")]
    ])
    await callback.message.edit_text(
        "Выберите тип вклада:\n\n"
        "💎 Сберегательный — от 10 000 ₽, срок 3 мес.\n"
        "🏆 Премиум — от 100 000 ₽, срок 6 мес.\n"
        "📅 Годовой — от 500 000 ₽, срок 12 мес.",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("deposit_open_"))
async def deposit_open(callback: types.CallbackQuery):
    rate = float(callback.data.split("_")[-1])
    amounts = {8: 10000, 10: 100000, 12: 500000}
    months = {8: 3, 10: 6, 12: 12}
    names = {8: "Сберегательный", 10: "Премиум", 12: "Годовой"}
    
    user = get_user(callback.from_user.id)
    amount = amounts[rate]
    
    if user["balance"] < amount:
        await callback.message.edit_text(f"❌ Недостаточно средств. Нужно: {amount:,} ₽")
        return
    
    user["balance"] -= amount
    deposit = {
        "type": names[rate],
        "amount": amount,
        "rate": rate,
        "end_date": f"{months[rate]} мес."
    }
    user["deposits"].append(deposit)
    user["operations"].append(f"Открыт вклад {names[rate]}: -{amount:,.0f} ₽")
    
    await callback.message.edit_text(
        f"✅ Вклад открыт!\n\n"
        f"Тип: {names[rate]}\n"
        f"Сумма: {amount:,} ₽\n"
        f"Ставка: {rate}% годовых\n"
        f"Срок: {months[rate]} мес."
    )

# ===== ИСТОРИЯ ОПЕРАЦИЙ =====

@dp.message(F.text == "📜 История операций")
async def show_history(message: Message):
    user = get_user(message.from_user.id)
    if not user["operations"]:
        await message.answer("История операций пуста.")
    else:
        text = "📜 <b>История операций:</b>\n\n"
        for i, op in enumerate(reversed(user["operations"][-10:]), 1):
            text += f"{i}. {op}\n"
        await message.answer(text, parse_mode="HTML")

# ===== НЕДВИЖИМОСТЬ =====

@dp.message(F.text == "🏠 Недвижимость")
async def property_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Моя собственность", callback_data="prop_my")],
        [InlineKeyboardButton(text="➕ Зарегистрировать", callback_data="prop_register")],
        [InlineKeyboardButton(text="🔍 На продажу", callback_data="prop_sale_list")],
        [InlineKeyboardButton(text="💰 Продать свою", callback_data="prop_sell")]
    ])
    await message.answer("Раздел недвижимости:", reply_markup=keyboard)

@dp.callback_query(F.data == "prop_my")
async def prop_my(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user["properties"]:
        await callback.message.edit_text("У вас нет зарегистрированной собственности.")
    else:
        text = "🏠 <b>Ваша собственность:</b>\n\n"
        for i, prop in enumerate(user["properties"], 1):
            text += f"{i}. {prop['type']}: {prop['address']}\n   Площадь: {prop['area']} м², Цена: {prop['price']:,.0f} ₽\n\n"
        await callback.message.edit_text(text, parse_mode="HTML")

@dp.callback_query(F.data == "prop_register")
async def prop_register(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    new_prop = {
        "type": "Квартира",
        "address": "ул. Ленина, д. 10, кв. 5",
        "area": 65,
        "price": 8500000
    }
    user["properties"].append(new_prop)
    user["operations"].append("Регистрация недвижимости: Квартира ул. Ленина")
    await callback.message.edit_text(
        "✅ Недвижимость зарегистрирована!\n\n"
        "Тип: Квартира\n"
        "Адрес: ул. Ленина, д. 10, кв. 5\n"
        "Площадь: 65 м²\n"
        "Оценочная стоимость: 8 500 000 ₽"
    )

@dp.callback_query(F.data == "prop_sale_list")
async def prop_sale_list(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔍 <b>Недвижимость на продажу:</b>\n\n"
        "1. 🏠 Дом, с. Вяземское\n   120 м², участок 8 сот.\n   💰 5 500 000 ₽\n\n"
        "2. 🏢 Квартира, г. Москва\n   45 м², 5/9 этаж\n   💰 12 000 000 ₽\n\n"
        "3. 🏡 Коттедж, пос. Зеленый\n   250 м², участок 15 сот.\n   💰 18 000 000 ₽",
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "prop_sell")
async def prop_sell(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user["properties"]:
        await callback.message.edit_text("❌ У вас нет недвижимости для продажи.")
        return
    
    prop = user["properties"].pop(0)
    user["balance"] += prop["price"]
    user["operations"].append(f"Продажа недвижимости: +{prop['price']:,.0f} ₽")
    await callback.message.edit_text(
        f"✅ Недвижимость продана!\n\n"
        f"{prop['type']}: {prop['address']}\n"
        f"Сумма: {prop['price']:,.0f} ₽\n\n"
        f"Средства зачислены на баланс."
    )

# ===== QR-ПЕРЕВОДЫ =====

@dp.message(F.text == "📷 QR-переводы")
async def qr_menu(message: Message):
    user = get_user(message.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Отправить по QR", callback_data="qr_send")],
        [InlineKeyboardButton(text="📥 Получить по QR", callback_data="qr_receive")]
    ])
    await message.answer(
        f"📷 <b>QR-переводы</b>\n\n"
        f"Ваш QR-код: <code>{user['qr_code']}</code>\n\n"
        f"Поделитесь этим кодом для получения переводов.",
        parse_mode="HTML",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "qr_send")
async def qr_send(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📤 <b>Отправка по QR</b>\n\n"
        "Введите QR-код получателя и сумму через пробел:\n"
        "Пример: <code>QR123456789 1000</code>\n\n"
        "Или вернитесь в меню.",
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "qr_receive")
async def qr_receive(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    await callback.message.edit_text(
        f"📥 <b>Ваш QR-код для получения:</b>\n\n"
        f"<code>{user['qr_code']}</code>\n\n"
        f"Отправьте этот код отправителю.",
        parse_mode="HTML"
    )

@dp.message(F.text.regexp(r"^QR\d+\s+\d+$"))
async def process_qr_transfer(message: Message):
    parts = message.text.split()
    qr_code = parts[0]
    amount = float(parts[1])
    
    sender = get_user(message.from_user.id)
    
    if sender["balance"] < amount:
        await message.answer("❌ Недостаточно средств.")
        return
    
    # Находим получателя по QR
    recipient = None
    for uid, data in users_db.items():
        if data["qr_code"] == qr_code and uid != message.from_user.id:
            recipient = data
            break
    
    if not recipient:
        await message.answer("❌ Получатель с таким QR-кодом не найден.")
        return
    
    sender["balance"] -= amount
    recipient["balance"] += amount
    sender["operations"].append(f"QR-перевод {qr_code}: -{amount:,.0f} ₽")
    recipient["operations"].append(f"QR-перевод от {message.from_user.id}: +{amount:,.0f} ₽")
    
    await message.answer(f"✅ Перевод выполнен!\n\nСумма: {amount:,.0f} ₽\nПолучатель: {qr_code}")

# ===== ЗАПУСК =====

async def main():
    print("Банковский бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
