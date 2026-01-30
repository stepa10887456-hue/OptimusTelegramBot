import logging
import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)

API_TOKEN = '8509137282:AAFZZmmtw3laqW_HAyY8mlW-gjdapkxJk9M'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Словарик для хранения связок Юзер:Группа (в идеале сюда нужна БД)
user_groups = {} 
spam_tasks = {}

class OptimusStates(StatesGroup):
    waiting_for_spam = State()

# --- МИНИ-СЕРВЕР ДЛЯ RENDER ---
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

# --- МЕНЮ ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="➕ Добавить в группу", url=f"https://t.me/Optimusbylumoxv2_bot?startgroup=true"))
    builder.row(types.InlineKeyboardButton(text="🚀 Спам-функция", callback_data="spam_setup"))
    builder.row(types.InlineKeyboardButton(text="🔍 Сканировать группу", callback_data="scan_info"))
    builder.row(types.InlineKeyboardButton(text="🔗 Получить ссылку", callback_data="get_link"))
    return builder.as_markup()

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer("🤖 **Optimus v2.0** запущен.\nУправляй функциями через кнопки ниже:", reply_markup=get_main_menu())

# --- ФУНКЦИЯ СПАМА ---
@dp.callback_query(F.data == "spam_setup")
async def spam_setup(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(OptimusStates.waiting_for_spam)
    await callback.message.answer("Введите данные для спама в формате:\n`Кол-во | Текст` (например: `5 | Привет`)")
    await callback.answer()

@dp.message(OptimusStates.waiting_for_spam)
async def run_spam(message: types.Message, state: FSMContext):
    if '|' not in message.text:
        return await message.answer("❌ Неверный формат! Используй: `Число | Текст`")
    
    parts = message.text.split('|', 1)
    count = int(parts[0].strip())
    text = parts[1].strip()
    user_id = message.from_user.id
    
    # Ищем группу, в которую юзер добавил бота
    chat_id = user_groups.get(user_id)
    if not chat_id:
        return await message.answer("❌ Я не знаю куда спамить! Сначала добавь меня в группу.")

    await state.clear()
    spam_tasks[chat_id] = True
    await message.answer(f"🚀 Запускаю спам в группу...")

    for i in range(count):
        if chat_id not in spam_tasks: break
        try:
            await bot.send_message(chat_id, text)
            await asyncio.sleep(0.7)
        except: break
    
    await message.answer("✅ Готово!")

# --- ПОЛУЧИТЬ ССЫЛКУ ---
@dp.callback_query(F.data == "get_link")
async def get_link_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    chat_id = user_groups.get(user_id)
    
    if not chat_id:
        return await callback.message.answer("❌ Нет данных о группе. Добавь меня куда-нибудь!")

    try:
        link = await bot.export_chat_invite_link(chat_id)
        await bot.send_message(user_id, f"🔗 Ссылка на вашу группу:\n{link}")
        await callback.answer("Ссылка отправлена!")
    except:
        await callback.message.answer("❌ Не удалось создать ссылку. Проверь, админ ли я в группе.")

# --- СКАНЕР ---
@dp.callback_query(F.data == "scan_info")
async def scan_info(callback: types.CallbackQuery):
    await callback.message.answer("Просто напиши `/scan` в своей группе, и я пришлю отчет сюда.")
    await callback.answer()

@dp.message(Command("scan"))
async def cmd_scan(message: types.Message):
    if message.chat.type == "private": return
    
    user_id = message.from_user.id
    try:
        admins = await bot.get_chat_administrators(message.chat.id)
        report = f"📊 **Отчет: {message.chat.title}**\nАдминов: {len(admins)}\nСтатус: Работает штатно ✅"
        await bot.send_message(user_id, report)
        await message.answer("🔍 Результат отправлен в ЛС.")
    except:
        await message.answer("Дайте мне права админа!")

# --- ЗАПОМИНАНИЕ ГРУППЫ ---
@dp.my_chat_member()
async def on_bot_added(event: types.ChatMemberUpdated):
    if event.new_chat_member.status in ["member", "administrator"]:
        # Запоминаем, кто добавил бота и в какой чат
        user_groups[event.from_user.id] = event.chat.id
        try:
            await bot.send_message(event.from_user.id, f"✅ Бот успешно подключен к группе: {event.chat.title}")
        except: pass

async def main():
    await asyncio.gather(start_background_web(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())