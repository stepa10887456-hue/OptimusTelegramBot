import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

logging.basicConfig(level=logging.INFO)

API_TOKEN = '7408761842:AAHrCeJ5upJUQmCQGD0Dz6treBBnnNoByio'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

registered_users = set()
spam_tasks = {} # Для хранения запущенных задач спама

# --- Клавиатуры ---
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

# --- Обработчики ---

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

# --- ФУНКЦИЯ СПАМА ---
# Инструкция: /spam [текст] [кол-во] в чате или личке
@dp.message(Command("spam"))
async def start_spam(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return await message.answer("Используй: `/spam [кол-во] [текст]`\nПример: `/spam 10 Привет!`")
    
    count = int(args[1])
    text = args[2]
    chat_id = message.chat.id
    
    stop_btn = InlineKeyboardBuilder()
    stop_btn.row(types.InlineKeyboardButton(text="🛑 ОСТАНОВИТЬ", callback_data=f"stop_spam_{chat_id}"))
    
    spam_tasks[chat_id] = True
    await message.answer(f"🚀 Запускаю спам ({count} раз)...", reply_markup=stop_btn.as_markup())

    for i in range(count):
        if chat_id not in spam_tasks: break # Если нажали стоп
        await bot.send_message(chat_id, text)
        await asyncio.sleep(0.5) # Небольшая пауза, чтобы Telegram не забанил сразу
    
    if chat_id in spam_tasks: del spam_tasks[chat_id]

@dp.callback_query(F.data.startswith("stop_spam_"))
async def stop_spam_handler(callback: types.CallbackQuery):
    chat_id = int(callback.data.split("_")[2])
    if chat_id in spam_tasks:
        del spam_tasks[chat_id]
        await callback.answer("Остановка...")
        await callback.message.edit_text("🛑 Спам остановлен.")
    else:
        await callback.answer("Спам уже не идет.")

# --- ИЗУЧЕНИЕ ГРУППЫ ---
@dp.callback_query(F.data == "scan_group")
async def scan_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("Чтобы изучить группу, добавь меня туда админом и напиши команду `/scan` прямо в чате группы.", reply_markup=get_back_button())

@dp.message(Command("scan"))
async def cmd_scan(message: types.Message):
    if message.chat.type == "private":
        return await message.answer("Эту команду нужно писать в группе!")
    
    status_msg = await message.answer("🔍 Начинаю анализ группы...")
    
    try:
        admins = await bot.get_chat_administrators(message.chat.id)
        # Внимание: получить ВСЕХ участников ботом нельзя (ограничение Telegram), 
        # можно только проверить текущие права и список админов.
        
        report = (
            f"📊 **Отчет по группе: {message.chat.title}**\n\n"
            f"👤 Админов найдено: {len(admins)}\n"
            f"🤖 Мои права: {'Админ' if any(a.user.id == bot.id for a in admins) else 'Участник'}\n"
        )
        
        # Проверка уязвимостей
        chat = await bot.get_chat(message.chat.id)
        vulnerabilities = []
        if not chat.permissions.can_send_messages: vulnerabilities.append("- Чат полностью закрыт")
        if chat.permissions.can_invite_users: vulnerabilities.append("- ⚠️ Обычные юзеры могут добавлять кого угодно")
        if chat.permissions.can_pin_messages: vulnerabilities.append("- ⚠️ Обычные юзеры могут крепить сообщения")
        
        if not vulnerabilities:
            report += "\n✅ Критических уязвимостей настроек не найдено."
        else:
            report += "\n⚠️ **Уязвимости:**\n" + "\n".join(vulnerabilities)

        await status_msg.edit_text(report)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка при сканировании: {e}\n(Сделайте меня админом!)")

# --- ЛОГИКА ПРИ ДОБАВЛЕНИИ ---
@dp.my_chat_member()
async def on_bot_added(event: types.ChatMemberUpdated):
    if event.new_chat_member.status in ["member", "administrator"]:
        adder_id = event.from_user.id
        if adder_id in registered_users:
            try:
                invite_link = await bot.export_chat_invite_link(event.chat.id)
                await bot.send_message(adder_id, f"✅ Подключен к: {event.chat.title}\nСсылка: {invite_link}")
            except:
                await bot.send_message(event.chat.id, "Сделайте меня админом, чтобы я прислал ссылку!")
        else:
            await bot.send_message(event.chat.id, "Ошибка! Пользователь не записан в Optimus.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())