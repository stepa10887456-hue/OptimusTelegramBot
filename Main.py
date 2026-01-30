import logging
import asyncio
import threading
import os
from aiohttp import web  # Нужно для мини-сервера
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Твой НОВЫЙ токен
API_TOKEN = '8509137282:AAFZZmmtw3laqW_HAyY8mlW-gjdapkxJk9M'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

registered_users = set()
spam_tasks = {}

# --- МИНИ-СЕРВЕР ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="Optimus is alive!")

async def start_background_web():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render дает порт в переменной окружения PORT, по умолчанию 10000
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

# --- КЛАВИАТУРЫ ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="➕ Добавить в группу", url=f"https://t.me/Optimusbylumox_bot?startgroup=true"))
    builder.row(types.InlineKeyboardButton(text="📝 Записать юзера", callback_data="register_me"))
    builder.row(types.InlineKeyboardButton(text="🚀 Спам-функция", callback_data="spam_menu"))
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
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text("Главное меню Optimus:", reply_markup=get_main_menu())

@dp.callback_query(F.data == "register_me")
async def register_callback(callback: types.CallbackQuery):
    registered_users.add(callback.from_user.id)
    await callback.message.edit_text("✅ Ты успешно записан в базу!", reply_markup=get_back_button())

# --- СПАМ ---
@dp.message(Command("spam"))
async def start_spam(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.answer("Используй: `/spam [кол-во] [текст]`")
    
    count = int(args[1])
    text = args[2]
    chat_id = message.chat.id
    
    stop_btn = InlineKeyboardBuilder()
    stop_btn.row(types.InlineKeyboardButton(text="🛑 ОСТАНОВИТЬ", callback_data=f"stop_spam_{chat_id}"))
    
    spam_tasks[chat_id] = True
    await message.answer(f"🚀 Запускаю спам ({count} раз)...", reply_markup=stop_btn.as_markup())

    for i in range(count):
        if chat_id not in spam_tasks: break
        try:
            await bot.send_message(chat_id, text)
            await asyncio.sleep(0.6) 
        except Exception:
            await asyncio.sleep(2) # Если лимит — притормаживаем
    
    if chat_id in spam_tasks: del spam_tasks[chat_id]

@dp.callback_query(F.data.startswith("stop_spam_"))
async def stop_spam_handler(callback: types.CallbackQuery):
    chat_id = int(callback.data.split("_")[2])
    if chat_id in spam_tasks:
        del spam_tasks[chat_id]
        await callback.message.edit_text("🛑 Спам остановлен.")

# --- СКАНЕР ---
@dp.callback_query(F.data == "scan_group")
async def scan_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("Добавь меня в группу админом и напиши `/scan` прямо там.", reply_markup=get_back_button())

@dp.message(Command("scan"))
async def cmd_scan(message: types.Message):
    if message.chat.type == "private":
        return await message.answer("Пиши эту команду в группе!")
    
    status_msg = await message.answer("🔍 Анализирую...")
    try:
        admins = await bot.get_chat_administrators(message.chat.id)
        chat = await bot.get_chat(message.chat.id)
        
        report = f"📊 **Группа: {message.chat.title}**\n👤 Админов: {len(admins)}\n"
        
        vulnerabilities = []
        if chat.permissions.can_invite_users: vulnerabilities.append("- Юзеры могут спамить инвайтами")
        if chat.permissions.can_pin_messages: vulnerabilities.append("- Юзеры могут менять закрепы")
        
        report += "\n⚠️ **Уязвимости:**\n" + "\n".join(vulnerabilities) if vulnerabilities else "\n✅ Дыр в настройках нет."
        await status_msg.edit_text(report)
    except Exception as e:
        await status_msg.edit_text(f"❌ Нужны права админа!")

# --- ДОБАВЛЕНИЕ В ГРУППУ ---
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
        else:
            await bot.send_message(event.chat.id, "Ошибка! Сначала нажми 'Записать юзера' в личке бота.")

async def main():
    # Запускаем веб-сервер и бота одновременно
    await asyncio.gather(start_background_web(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())