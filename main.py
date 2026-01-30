import logging
import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Настройка логов
logging.basicConfig(level=logging.INFO)

API_TOKEN = '8509137282:AAFZZmmtw3laqW_HAyY8mlW-gjdapkxJk9M'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

registered_users = set()
spam_tasks = {}

# Состояния для ожидания ввода от юзера
class SpamStates(StatesGroup):
    waiting_for_spam_data = State()

# --- МИНИ-СЕРВЕР ---
async def handle(request):
    return web.Response(text="Optimus is alive!")

async def start_background_web():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- КЛАВИАТУРЫ ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="➕ Добавить в группу", url=f"https://t.me/Optimusbylumox_bot?startgroup=true"))
    builder.row(types.InlineKeyboardButton(text="📝 Записать юзера", callback_data="register_me"))
    builder.row(types.InlineKeyboardButton(text="🚀 Спам-функция", callback_data="spam_setup"))
    builder.row(types.InlineKeyboardButton(text="🔍 Изучить группу", callback_data="scan_group"))
    return builder.as_markup()

def get_back_button():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"))
    return builder.as_markup()

# --- ОБРАБОТЧИКИ ---

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("Привет! Я **Optimus**. Выбери действие:", reply_markup=get_main_menu())

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear() # Сбрасываем ожидания, если юзер передумал
    await callback.message.edit_text("Главное меню Optimus:", reply_markup=get_main_menu())

@dp.callback_query(F.data == "register_me")
async def register_callback(callback: types.CallbackQuery):
    registered_users.add(callback.from_user.id)
    await callback.message.edit_text("✅ Ты успешно записан в базу!", reply_markup=get_back_button())

# --- НОВАЯ СПАМ-ФУНКЦИЯ (ЧЕРЕЗ КНОПКУ) ---
@dp.callback_query(F.data == "spam_setup")
async def spam_setup(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SpamStates.waiting_for_spam_data)
    await callback.message.edit_text(
        "🚀 **Настройка спама**\n\nПришли сообщение в формате:\n`Количество | Текст`\n\nНапример:\n`5 | Всем привет!`",
        reply_markup=get_back_button()
    )

@dp.message(SpamStates.waiting_for_spam_data)
async def process_spam_input(message: types.Message, state: FSMContext):
    if '|' not in message.text:
        return await message.answer("❌ Ошибка! Используй разделитель `|` (например: 10 | привет)")
    
    parts = message.text.split('|', 1)
    try:
        count = int(parts[0].strip())
        text = parts[1].strip()
        chat_id = message.chat.id
        
        await state.clear()
        
        stop_btn = InlineKeyboardBuilder()
        stop_btn.row(types.InlineKeyboardButton(text="🛑 ОСТАНОВИТЬ", callback_data=f"stop_spam_{chat_id}"))
        
        spam_tasks[chat_id] = True
        await message.answer(f"🚀 Запускаю спам ({count} раз)...", reply_markup=stop_btn.as_markup())

        for i in range(count):
            if chat_id not in spam_tasks: break
            try:
                await bot.send_message(chat_id, text)
                await asyncio.sleep(0.7)
            except Exception:
                await asyncio.sleep(3)
        
        if chat_id in spam_tasks: del spam_tasks[chat_id]
        await message.answer("✅ Спам завершен.")

    except ValueError:
        await message.answer("❌ Первое число должно быть количеством!")

@dp.callback_query(F.data.startswith("stop_spam_"))
async def stop_spam_handler(callback: types.CallbackQuery):
    chat_id = int(callback.data.split("_")[2])
    if chat_id in spam_tasks:
        del spam_tasks[chat_id]
        await callback.message.edit_text("🛑 Спам остановлен.")

# --- СКАНЕР (ОТПРАВКА В ЛС) ---
@dp.callback_query(F.data == "scan_group")
async def scan_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Чтобы изучить группу, добавь меня туда админом и напиши команду `/scan` прямо в чате. Результат придет тебе в ЛС!", 
        reply_markup=get_back_button()
    )

@dp.message(Command("scan"))
async def cmd_scan(message: types.Message):
    if message.chat.type == "private":
        return await message.answer("Эту команду нужно писать в группе!")
    
    user_id = message.from_user.id # Тот, кто вызвал скан
    
    try:
        admins = await bot.get_chat_administrators(message.chat.id)
        chat = await bot.get_chat(message.chat.id)
        
        report = (
            f"🔍 **Результат сканирования группы: {message.chat.title}**\n\n"
            f"👤 Администраторов: {len(admins)}\n"
        )
        
        vulnerabilities = []
        if chat.permissions.can_invite_users: vulnerabilities.append("— Обычные пользователи могут спамить инвайтами.")
        if chat.permissions.can_pin_messages: vulnerabilities.append("— Обычные пользователи могут менять закрепы.")
        
        if vulnerabilities:
            report += "⚠️ **Найдены уязвимости в настройках:**\n" + "\n".join(vulnerabilities)
        else:
            report += "✅ Группа настроена безопасно."

        # Отправляем результат В ЛИЧКУ
        await bot.send_message(user_id, report)
        # А в группе просто подтверждаем выполнение
        await message.answer("🔍 Анализ завершен. Результаты отправлены вам в личные сообщения.")
        
    except Exception as e:
        await message.answer("❌ Ошибка! Скорее всего, вы не написали мне в личку (нажмите /start) или я не админ.")

# --- ЛОГИКА ДОБАВЛЕНИЯ ---
@dp.my_chat_member()
async def on_bot_added(event: types.ChatMemberUpdated):
    if event.new_chat_member.status in ["member", "administrator"]:
        adder_id = event.from_user.id
        if adder_id in registered_users:
            try:
                invite_link = await bot.export_chat_invite_link(event.chat.id)
                await bot.send_message(adder_id, f"✅ Подключен к: {event.chat.title}\n{invite_link}")
            except:
                await bot.send_message(event.chat.id, "Дайте мне права админа для ссылки!")

async def main():
    await asyncio.gather(start_background_web(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())