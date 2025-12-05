import telebot
from telebot import types
import json
import os
from datetime import datetime

# ==================== КОНФИГУРАЦИЯ ====================
TOKEN = '7735676303:AAEql8xom6w-5uU-kyk0Ca_sM4dPMnMli2o'
ADMIN_GROUP_ID = -1003374135501
OWNER_ID = 6763156697
DIALOG_TOPIC_ID = 3

bot = telebot.TeleBot(TOKEN)

# ==================== ХРАНИЛИЩЕ ДАННЫХ ====================
users = {}
stats = {
    'totalUsers': 0,
    'bannedUsers': 0,
    'messagesPerDay': 0,
    'lastReset': datetime.now().strftime('%Y-%m-%d')
}

# Хранилище для связи сообщений
message_links = {}  # {client_message_id: admin_message_id, admin_message_id: client_message_id}

def load_data():
    global users, stats, message_links
    try:
        if os.path.exists('users.json'):
            with open('users.json', 'r', encoding='utf-8') as f:
                users = json.load(f)
        if os.path.exists('stats.json'):
            with open('stats.json', 'r', encoding='utf-8') as f:
                stats = json.load(f)
        if os.path.exists('message_links.json'):
            with open('message_links.json', 'r', encoding='utf-8') as f:
                message_links = json.load(f)
    except Exception as e:
        print(f'Ошибка загрузки данных: {e}')

def save_data():
    try:
        with open('users.json', 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        with open('stats.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        with open('message_links.json', 'w', encoding='utf-8') as f:
            json.dump(message_links, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'Ошибка сохранения данных: {e}')

def reset_daily_stats():
    today = datetime.now().strftime('%Y-%m-%d')
    if stats['lastReset'] != today:
        stats['messagesPerDay'] = 0
        stats['lastReset'] = today
        save_data()

def register_user(user_id, username, first_name):
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {
            'username': username or 'Без username',
            'firstName': first_name or 'Пользователь',
            'banned': False,
            'warns': 0,
            'lastMessageId': None,
            'registered': datetime.now().isoformat()
        }
        stats['totalUsers'] += 1
        save_data()

# ==================== START КОМАНДА ====================
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    register_user(user_id, username, first_name)
    
    welcome_text = """👋 Добро пожаловать в службу поддержки!

📋 **ВАЖНЫЕ ПРАВИЛА:**

1️⃣ Используй хештег своего админа при диалоге (#админ)
   При несоблюдении этой нормы будет выдан варн ⚠️

2️⃣ Прочти описание группы - там важная информация о нашей команде и системе бота

✅ Теперь можешь написать свой вопрос, и он будет передан администраторам."""
    
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')

# ==================== СТАТИСТИКА ====================
@bot.message_handler(commands=['stat'])
def stat_handler(message):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        bot.send_message(message.chat.id, '❌ У вас нет доступа к этой команде')
        return
    
    reset_daily_stats()
    
    banned_count = sum(1 for u in users.values() if u['banned'])
    
    stats_text = f"""📊 **СТАТИСТИКА БОТА**

👥 Всего клиентов: {stats['totalUsers']}
🚫 Забанено: {banned_count}
📨 Сообщений за день: {stats['messagesPerDay']}
📅 Дата: {datetime.now().strftime('%d.%m.%Y')}

⏰ Последний сброс: {stats['lastReset']}"""
    
    bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')

# ==================== РАССЫЛКА ====================
@bot.message_handler(commands=['rass'])
def rass_handler(message):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        bot.send_message(message.chat.id, '❌ У вас нет доступа к этой команде')
        return
    
    text_parts = message.text.split(' ', 1)
    if len(text_parts) < 2:
        bot.send_message(message.chat.id, '❌ Использование: /rass [текст]')
        return
    
    message_text = text_parts[1]
    sent = 0
    failed = 0
    
    bot.send_message(message.chat.id, '📤 Начинаю рассылку...')
    
    for uid, user_data in users.items():
        if not user_data['banned']:
            try:
                bot.send_message(int(uid), f"📢 **РАССЫЛКА ОТ АДМИНИСТРАЦИИ:**\n\n{message_text}", parse_mode='Markdown')
                sent += 1
            except:
                failed += 1
    
    bot.send_message(message.chat.id, f"✅ Рассылка завершена!\n\n📨 Отправлено: {sent}\n❌ Не доставлено: {failed}")

# ==================== БАН ====================
@bot.message_handler(commands=['ban'])
def ban_handler(message):
    if message.chat.id != ADMIN_GROUP_ID:
        return
    if not message.reply_to_message:
        bot.send_message(message.chat.id, '❌ Ответьте на сообщение пользователя', message_thread_id=message.message_thread_id)
        return
    
    # Ищем ID клиента
    client_id = None
    if message.reply_to_message.forward_from:
        client_id = str(message.reply_to_message.forward_from.id)
    else:
        # Ищем по message_id
        for uid, user_data in users.items():
            if user_data.get('lastMessageId') == message.reply_to_message.message_id:
                client_id = uid
                break
    
    if not client_id:
        bot.send_message(message.chat.id, '❌ Не удалось определить пользователя', message_thread_id=message.message_thread_id)
        return
    
    if client_id in users:
        users[client_id]['banned'] = True
        save_data()
        
        bot.send_message(ADMIN_GROUP_ID, f"🚫 Пользователь @{users[client_id]['username']} забанен", message_thread_id=message.message_thread_id)
        try:
            bot.send_message(int(client_id), '🚫 Вы были заблокированы администрацией. Обращения больше не принимаются.')
        except:
            pass

# ==================== РАЗБАН ====================
@bot.message_handler(commands=['unban'])
def unban_handler(message):
    if message.chat.id != ADMIN_GROUP_ID:
        return
    if not message.reply_to_message:
        bot.send_message(message.chat.id, '❌ Ответьте на сообщение пользователя', message_thread_id=message.message_thread_id)
        return
    
    # Ищем ID клиента
    client_id = None
    if message.reply_to_message.forward_from:
        client_id = str(message.reply_to_message.forward_from.id)
    else:
        for uid, user_data in users.items():
            if user_data.get('lastMessageId') == message.reply_to_message.message_id:
                client_id = uid
                break
    
    if not client_id:
        bot.send_message(message.chat.id, '❌ Не удалось определить пользователя', message_thread_id=message.message_thread_id)
        return
    
    if client_id in users:
        users[client_id]['banned'] = False
        users[client_id]['warns'] = 0
        save_data()
        
        bot.send_message(ADMIN_GROUP_ID, f"✅ Пользователь @{users[client_id]['username']} разбанен", message_thread_id=message.message_thread_id)
        try:
            bot.send_message(int(client_id), '✅ Вы были разблокированы. Теперь можете снова писать в поддержку.')
        except:
            pass

# ==================== ВАРН ====================
@bot.message_handler(commands=['warn'])
def warn_handler(message):
    if message.chat.id != ADMIN_GROUP_ID:
        return
    if not message.reply_to_message:
        bot.send_message(message.chat.id, '❌ Ответьте на сообщение пользователя', message_thread_id=message.message_thread_id)
        return
    
    # Получаем причину варна (если есть)
    text_parts = message.text.split(' ', 1)
    warn_reason = text_parts[1] if len(text_parts) > 1 else None
    
    # Ищем ID клиента
    client_id = None
    if message.reply_to_message.forward_from:
        client_id = str(message.reply_to_message.forward_from.id)
    else:
        for uid, user_data in users.items():
            if user_data.get('lastMessageId') == message.reply_to_message.message_id:
                client_id = uid
                break
    
    if not client_id:
        bot.send_message(message.chat.id, '❌ Не удалось определить пользователя', message_thread_id=message.message_thread_id)
        return
    
    if client_id in users:
        users[client_id]['warns'] += 1
        
        if users[client_id]['warns'] >= 3:
            users[client_id]['banned'] = True
            admin_msg = f"🚫 Пользователь @{users[client_id]['username']} получил 3 варна и автоматически забанен"
            if warn_reason:
                admin_msg += f"\n📝 Причина последнего варна: {warn_reason}"
            bot.send_message(ADMIN_GROUP_ID, admin_msg, message_thread_id=message.message_thread_id)
            
            client_msg = '🚫 Вы получили 3 предупреждения и были заблокированы.'
            if warn_reason:
                client_msg += f'\n📝 Причина: {warn_reason}'
            try:
                bot.send_message(int(client_id), client_msg)
            except:
                pass
        else:
            admin_msg = f"⚠️ Пользователь @{users[client_id]['username']} получил варн ({users[client_id]['warns']}/3)"
            if warn_reason:
                admin_msg += f"\n📝 Причина: {warn_reason}"
            bot.send_message(ADMIN_GROUP_ID, admin_msg, message_thread_id=message.message_thread_id)
            
            client_msg = f"⚠️ Вы получили предупреждение ({users[client_id]['warns']}/3). При 3 предупреждениях вы будете заблокированы."
            if warn_reason:
                client_msg += f'\n📝 Причина: {warn_reason}'
            try:
                bot.send_message(int(client_id), client_msg)
            except:
                pass
        
        save_data()

# ==================== СНЯТЬ ВАРН ====================
@bot.message_handler(commands=['unwarn'])
def unwarn_handler(message):
    if message.chat.id != ADMIN_GROUP_ID:
        return
    if not message.reply_to_message:
        bot.send_message(message.chat.id, '❌ Ответьте на сообщение пользователя', message_thread_id=message.message_thread_id)
        return
    
    # Ищем ID клиента
    client_id = None
    if message.reply_to_message.forward_from:
        client_id = str(message.reply_to_message.forward_from.id)
    else:
        for uid, user_data in users.items():
            if user_data.get('lastMessageId') == message.reply_to_message.message_id:
                client_id = uid
                break
    
    if not client_id:
        bot.send_message(message.chat.id, '❌ Не удалось определить пользователя', message_thread_id=message.message_thread_id)
        return
    
    if client_id in users and users[client_id]['warns'] > 0:
        users[client_id]['warns'] -= 1
        save_data()
        bot.send_message(ADMIN_GROUP_ID, f"✅ С пользователя @{users[client_id]['username']} снят варн ({users[client_id]['warns']}/3)", message_thread_id=message.message_thread_id)

# ==================== ОБРАБОТКА РЕДАКТИРОВАНИЯ СООБЩЕНИЙ ====================
@bot.edited_message_handler(content_types=['text'])
def handle_edited_message(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    
    # Если сообщение отредактировано в группе админов (админ редактирует свой ответ)
    if chat_id == ADMIN_GROUP_ID:
        # Проверяем, есть ли связь с сообщением клиента
        if str(message.message_id) in message_links:
            client_message_id = message_links[str(message.message_id)]
            
            try:
                # Редактируем сообщение у клиента
                bot.edit_message_text(message.text, int(client_message_id.split('_')[0]), int(client_message_id.split('_')[1]))
                print(f'✅ Сообщение отредактировано у клиента')
            except Exception as e:
                print(f'Ошибка редактирования у клиента: {e}')
        return
    
    # Если сообщение отредактировано клиентом
    if user_id in users and users[user_id]['banned']:
        return
    
    # Ищем связанное сообщение в группе админов
    if str(message.message_id) in message_links:
        admin_message_id = message_links[str(message.message_id)]
        
        try:
            # Редактируем сообщение в группе админов
            bot.edit_message_text(message.text, ADMIN_GROUP_ID, admin_message_id)
            print(f'✅ Сообщение отредактировано у админа')
        except Exception as e:
            print(f'Ошибка редактирования у админа: {e}')

# ==================== ПЕРЕСЫЛКА СООБЩЕНИЙ ====================
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'video_note', 'document', 'sticker', 'audio', 'animation', 'location', 'contact'])
def message_handler(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    
    # Пропускаем сообщения из группы админов
    if chat_id == ADMIN_GROUP_ID:
        # Проверяем, это ответ админа клиенту?
        if message.reply_to_message:
            # Ищем ID клиента
            client_id = None
            
            # Способ 1: через forward_from
            if message.reply_to_message.forward_from:
                client_id = message.reply_to_message.forward_from.id
            
            # Способ 2: ищем в сохранённых данных
            else:
                for uid, user_data in users.items():
                    if user_data.get('lastMessageId') == message.reply_to_message.message_id:
                        client_id = int(uid)
                        break
            
            if not client_id:
                return
            
            client_id_str = str(client_id)
            
            if client_id_str in users and users[client_id_str]['banned']:
                return
            
            try:
                # Отправляем ответ клиенту
                sent_message = None
                if message.text:
                    sent_message = bot.send_message(client_id, message.text)
                elif message.photo:
                    sent_message = bot.send_photo(client_id, message.photo[-1].file_id, caption=message.caption)
                elif message.video:
                    sent_message = bot.send_video(client_id, message.video.file_id, caption=message.caption)
                elif message.voice:
                    sent_message = bot.send_voice(client_id, message.voice.file_id)
                elif message.video_note:
                    sent_message = bot.send_video_note(client_id, message.video_note.file_id)
                elif message.document:
                    sent_message = bot.send_document(client_id, message.document.file_id, caption=message.caption)
                elif message.sticker:
                    sent_message = bot.send_sticker(client_id, message.sticker.file_id)
                elif message.audio:
                    sent_message = bot.send_audio(client_id, message.audio.file_id)
                elif message.animation:
                    sent_message = bot.send_animation(client_id, message.animation.file_id, caption=message.caption)
                elif message.location:
                    sent_message = bot.send_location(client_id, message.location.latitude, message.location.longitude)
                elif message.contact:
                    sent_message = bot.send_contact(client_id, message.contact.phone_number, message.contact.first_name)
                
                # Сохраняем связь сообщений для редактирования
                if sent_message:
                    # Сохраняем как client_chat_id_client_message_id
                    client_message_key = f"{client_id}_{sent_message.message_id}"
                    message_links[str(message.message_id)] = client_message_key
                    message_links[client_message_key] = message.message_id
                    save_data()
                    print(f'🔗 Связь сохранена: {message.message_id} -> {client_message_key}')
                    
            except Exception as e:
                print(f'Ошибка отправки ответа: {e}')
        return
    
    # Регистрируем пользователя
    register_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    # Проверка бана
    if user_id in users and users[user_id]['banned']:
        bot.send_message(chat_id, '🚫 Вы заблокированы и не можете отправлять сообщения')
        return
    
    # Обновляем статистику
    reset_daily_stats()
    stats['messagesPerDay'] += 1
    save_data()
    
    # Отправляем КОПИЮ сообщения в группу админов (не пересылку!)
    try:
        sent_message = None
        if message.text:
            user_info = f"👤 {users[user_id]['firstName']} (@{users[user_id]['username']})"
            sent_message = bot.send_message(ADMIN_GROUP_ID, f"{user_info}\n\n{message.text}", message_thread_id=DIALOG_TOPIC_ID)
        elif message.photo:
            user_info = f"👤 {users[user_id]['firstName']} (@{users[user_id]['username']})"
            caption = f"{user_info}\n\n{message.caption}" if message.caption else user_info
            sent_message = bot.send_photo(ADMIN_GROUP_ID, message.photo[-1].file_id, caption=caption, message_thread_id=DIALOG_TOPIC_ID)
        elif message.video:
            user_info = f"👤 {users[user_id]['firstName']} (@{users[user_id]['username']})"
            caption = f"{user_info}\n\n{message.caption}" if message.caption else user_info
            sent_message = bot.send_video(ADMIN_GROUP_ID, message.video.file_id, caption=caption, message_thread_id=DIALOG_TOPIC_ID)
        elif message.document:
            user_info = f"👤 {users[user_id]['firstName']} (@{users[user_id]['username']})"
            caption = f"{user_info}\n\n{message.caption}" if message.caption else user_info
            sent_message = bot.send_document(ADMIN_GROUP_ID, message.document.file_id, caption=caption, message_thread_id=DIALOG_TOPIC_ID)
        # Для остальных типов просто пересылаем (их редко редактируют)
        else:
            sent_message = bot.forward_message(ADMIN_GROUP_ID, chat_id, message.message_id, message_thread_id=DIALOG_TOPIC_ID)
        
        if sent_message:
            users[user_id]['lastMessageId'] = sent_message.message_id
            
            # Сохраняем связь сообщений для редактирования
            message_links[str(message.message_id)] = sent_message.message_id
            message_links[str(sent_message.message_id)] = message.message_id
            
            save_data()
            print(f'🔗 Связь сохранена: {message.message_id} -> {sent_message.message_id}')
    except Exception as e:
        print(f'Ошибка отправки сообщения админам: {e}')

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    load_data()
    print('🤖 Бот запущен!')
    bot.infinity_polling()