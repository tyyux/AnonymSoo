import os
import sqlite3
import telebot
from telebot import types

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("Токен не найден!")

bot = telebot.TeleBot(TOKEN)

DB_NAME = 'bot.db'
SUPPORT_USERNAME = '@WeryVarm0'
STARS_PRICE = 50

user_states = {}

# ============ БАЗА ДАННЫХ ============

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            sender_id INTEGER,
            text TEXT,
            paid INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ============ МЕНЮ ============

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🔗 Моя ссылка"),
        types.KeyboardButton("📊 Статистика"),
        types.KeyboardButton("💡 Помощь"),
        types.KeyboardButton("💌 Поддержка")
    )
    return markup

# ============ СТАРТ ============

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    args = message.text.split()
    if len(args) > 1 and args[1].startswith('user_'):
        try:
            owner_id = int(args[1].replace('user_', ''))
        except:
            bot.send_message(message.chat.id, "Неверная ссылка 😔")
            return

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute('SELECT user_id FROM users WHERE user_id = ?', (owner_id,))
        owner = cur.fetchone()
        conn.close()

        if not owner:
            bot.send_message(message.chat.id, "Автор не найден 😔")
            return

        if owner_id == user_id:
            bot.send_message(message.chat.id, "Это твоя же ссылка 🙂")
            return

        user_states[user_id] = {'action': 'ask', 'owner_id': owner_id}
        bot.send_message(
            message.chat.id,
            "✍️ Задай анонимный вопрос.\nПросто напиши его сюда 👇",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
    ''', (user_id, username, first_name))
    cur.execute('''
        UPDATE users SET username = ?, first_name = ? WHERE user_id = ?
    ''', (username, first_name, user_id))
    conn.commit()
    conn.close()

    bot_username = bot.get_me().username
    link = f"https://t.me/{bot_username}?start=user_{user_id}"

    bot.send_message(
        message.chat.id,
        f"✨ Привет, {first_name}!\n\n"
        f"🔗 Твоя личная ссылка:\n{link}\n\n"
        f"📩 Кидай её друзьям — они смогут задать тебе анонимный вопрос.",
        reply_markup=main_menu()
    )

# ============ КНОПКИ МЕНЮ ============

@bot.message_handler(func=lambda m: m.text == "🔗 Моя ссылка")
def show_link(message):
    user_id = message.from_user.id
    bot_username = bot.get_me().username
    link = f"https://t.me/{bot_username}?start=user_{user_id}"
    bot.send_message(
        message.chat.id,
        f"🔗 Твоя ссылка:\n{link}\n\nКидай её друзьям 👇",
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def show_stats(message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM questions WHERE owner_id = ?', (user_id,))
    total = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM questions WHERE owner_id = ? AND paid = 1', (user_id,))
    paid = cur.fetchone()[0]
    conn.close()
    bot.send_message(
        message.chat.id,
        f"📊 Твоя статистика:\n\n"
        f"📩 Всего вопросов: {total}\n"
        f"🔓 Раскрыто отправителей: {paid}\n"
        f"🕵️ Осталось анонимных: {total - paid}",
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: m.text == "💡 Помощь")
def show_help(message):
    bot.send_message(
        message.chat.id,
        "💡 Как пользоваться ботом:\n\n"
        "1️⃣ Получи свою ссылку\n"
        "2️⃣ Кидай её друзьям\n"
        "3️⃣ Они пишут тебе анонимно\n"
        "4️⃣ Можешь ответить или узнать отправителя за 50 ⭐\n\n"
        "Всё просто! 🚀",
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: m.text == "💌 Поддержка")
def show_support(message):
    bot.send_message(
        message.chat.id,
        f"💌 Поддержка:\n\n"
        f"Если что-то не работает или есть вопросы — пиши:\n{SUPPORT_USERNAME}",
        reply_markup=main_menu()
    )

# ============ ПРИЁМ ВОПРОСА ============

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('action') == 'ask')
def receive_question(message):
    sender_id = message.from_user.id
    owner_id = user_states[sender_id]['owner_id']
    text = message.text

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO questions (owner_id, sender_id, text)
        VALUES (?, ?, ?)
    ''', (owner_id, sender_id, text))
    question_id = cur.lastrowid
    conn.commit()
    conn.close()

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🕵️ Кто это? — 50 ⭐", callback_data=f"reveal_{question_id}"),
        types.InlineKeyboardButton("✍️ Ответить", callback_data=f"reply_{question_id}"),
        types.InlineKeyboardButton("🗑️ Удалить", callback_data=f"hide_{question_id}")
    )

    try:
        bot.send_message(
            owner_id,
            f"📩 Анонимный вопрос:\n\n{text}",
            reply_markup=markup
        )
    except Exception as e:
        bot.send_message(sender_id, "Автор недоступен 😔")
        del user_states[sender_id]
        return

    bot.send_message(sender_id, "✅ Отправлено! Хочешь задать ещё? Просто напиши.")

# ============ КНОПКИ ПОД ВОПРОСОМ ============

@bot.callback_query_handler(func=lambda c: c.data.startswith('hide_'))
def hide_question(call):
    bot.edit_message_text(
        "🗑️ Вопрос удалён",
        call.message.chat.id,
        call.message.message_id
    )
    bot.answer_callback_query(call.id, "Удалено")

@bot.callback_query_handler(func=lambda c: c.data.startswith('reply_'))
def reply_question(call):
    question_id = int(call.data.replace('reply_', ''))
    user_states[call.from_user.id] = {'action': 'reply', 'question_id': question_id}
    bot.send_message(call.message.chat.id, "✍️ Напиши ответ на вопрос:")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('reveal_'))
def reveal_question(call):
    bot.answer_callback_query(call.id, "Оплата Stars будет позже 😊")
    bot.send_message(call.message.chat.id, "💎 Оплата Stars появится в следующем обновлении.")

# ============ ОТПРАВКА ОТВЕТА ============

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('action') == 'reply')
def send_reply(message):
    user_id = message.from_user.id
    question_id = user_states[user_id]['question_id']

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT sender_id FROM questions WHERE id = ?', (question_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        bot.send_message(message.chat.id, "Вопрос не найден 😔")
        del user_states[user_id]
        return

    sender_id = row[0]
    try:
        bot.send_message(sender_id, f"💬 Автор ответил на твой вопрос:\n\n{message.text}")
        bot.send_message(message.chat.id, "✅ Ответ отправлен!", reply_markup=main_menu())
    except:
        bot.send_message(message.chat.id, "Не удалось отправить 😔")

    del user_states[user_id]

# ============ ЗАПУСК ============

print('Бот запущен...')
bot.polling(none_stop=True)
