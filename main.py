import logging
import asyncio
import os
import re
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)

API_TOKEN = '8509137282:AAFZZmmtw3laqW_HAyY8mlW-gjdapkxJk9M'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Храним ID группы, куда добавили бота
# Формат: {id_юзера: id_группы}
user_groups = {}
spam_tasks = {}

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

# --- МЕНЮ (ТОЛЬКО В ЛС) ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="➕ Добавить в группу", url=f"https://t.me/Optimusbylumoxv2_bot?startgroup=true"))
    builder.row(types.InlineKeyboardButton(text="🔍 Сканировать группу", callback_data="scan_now"))
    builder.row(types.InlineKeyboardButton(text="🔗 Получить ссылку", callback_data="get_link"))
    builder.row(types.InlineKeyboardButton(text="🛑 Стоп спам", callback_data="stop_spam"))
    return builder.as_markup()

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    # Если написали в группе - игнорируем
    if message.chat.type != 'private':
        return
    
    await message.answer(
        "🤖 **Optimus Control Panel**\n\n"
        "📜 **Инструкция:**\n"
        "1. Добавь меня в группу админом.\n"
        "2. Чтобы запустить спам, напиши мне в ЛС:\n"
        "`!кол-во текст`\n"
        "Пример: `!5 Привет всем!`\n\n"
        "👇 Управление:", 
        reply_markup=get_main_menu()
    )

# --- СПАМ ПО ФОРМАТУ !10 ТЕКСТ ---
@dp.message(F.text.startswith("!"))
async def spam_command(message: types.Message):
    if message.chat.type != 'private': return # Только в личке

    # Парсим сообщение: ищем число после ! и текст
    # Пример: !10 Привет
    try:
        match = re.match(r'!(\d+)\s+(.+)', message.text)
        if not match:
            return await message.answer("❌ Неверный формат!\nПиши так: `!10 Привет`")

        count = int(match.group(1))
        text = match.group(2)
        user_id = message.from_user.id
        
        # Проверяем, привязан ли бот к группе
        target_chat_id = user_groups.get(user_id)
        if not target_chat_id:
            return await message.answer("❌ Я не знаю, куда писать! Сначала добавь меня в группу.")

        # Запуск
        spam_tasks[target_chat_id] = True
        await message.answer(f"🚀 Отправляю '{text}' {count} раз в группу...")

        for i in range(count):
            if target_chat_id not in spam_tasks: break
            try:
                await bot.send_message(target_chat_id, text)
                await asyncio.sleep(0.8) # Пауза, чтобы не забанили
            except Exception as e:
                await message.answer(f"⚠️ Ошибка отправки: {e}")
                break
        
        if target_chat_id in spam_tasks: del spam_tasks[target_chat_id]
        await message.answer("✅ Спам завершен.")

    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.callback_query(F.data == "stop_spam")
async def stop_spam_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    target_chat_id = user_groups.get(user_id)
    if target_chat_id and target_chat_id in spam_tasks:
        del spam_tasks[target_chat_id]
        await callback.answer("🛑 Остановлено!")
        await callback.message.answer("🛑 Спам принудительно остановлен.")
    else:
        await callback.answer("Спам сейчас не идет.")

# --- СКАНИРОВАНИЕ (ПО КНОПКЕ В ЛС) ---
@dp.callback_query(F.data == "scan_now")
async def scan_group_remote(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    target_chat_id = user_groups.get(user_id)

    if not target_chat_id:
        return await callback.message.answer("❌ Группа не найдена. Удалите меня из группы и добавьте снова.")

    try:
        chat = await bot.get_chat(target_chat_id)
        admins = await bot.get_chat_administrators(target_chat_id)
        
        report = (
            f"📊 **Анализ группы**\n"
            f"🏷 Название: {chat.title}\n"
            f"🆔 ID: `{chat.id}`\n"
            f"👮 Админов: {len(admins)}\n"
        )
        
        vulns = []
        if chat.permissions and chat.permissions.can_invite_users:
            vulns.append("⚠️ Доступен инвайт (обычные юзеры могут звать ботов)")
        if chat.permissions and chat.permissions.can_pin_messages:
            vulns.append("⚠️ Открыты закрепы")

        if vulns:
            report += "\n".join(vulns)
        else:
            report += "✅ Критических дыр в правах нет."

        await callback.message.answer(report)
        await callback.answer()
        
    except Exception as e:
        await callback.message.answer(f"❌ Не могу просканировать. Я еще админ там?\nОшибка: {e}")

# --- ПОЛУЧИТЬ ССЫЛКУ ---
@dp.callback_query(F.data == "get_link")
async def get_link_remote(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    target_chat_id = user_groups.get(user_id)
    
    if not target_chat_id:
        return await callback.message.answer("❌ Группа не найдена.")

    try:
        link = await bot.export_chat_invite_link(target_chat_id)
        await callback.message.answer(f"🔗 Ваша ссылка: {link}")
        await callback.answer()
    except:
        await callback.message.answer("❌ Ошибка. Дайте мне права 'Управление ссылками' в группе.")

# --- АВТО-ПРИВЯЗКА ПРИ ДОБАВЛЕНИИ ---
@dp.my_chat_member()
async def on_bot_added(event: types.ChatMemberUpdated):
    # Реагируем только если бота добавили или повысили права
    if event.new_chat_member.status in ["member", "administrator"]:
        user_id = event.from_user.id
        chat_id = event.chat.id
        
        # Запоминаем связку: Этот Юзер -> Эта Группа
        user_groups[user_id] = chat_id
        
        # Пишем ТОЛЬКО в личку юзеру, в группе молчим
        try:
            await bot.send_message(user_id, f"✅ Я подключен к группе **{event.chat.title}**!\nТеперь можешь управлять мной отсюда.")
        except:
            pass # Если личка закрыта, ничего не поделаешь

async def main():
    await asyncio.gather(start_background_web(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())