import os
import sqlite3
import telebot
from telebot import types

# ================== SOZLAMALAR ==================
# Token muammosi to'g'rilandi: endi u to'g'ridan-to'g'ri o'qiladi
TOKEN = "8651561210:AAGTxn21xZrxXZcY2i_ZEiWx6GTurz2IuvE"
CHANNEL = "@zeromaxgroup"   # kanal username
bot = telebot.TeleBot(TOKEN)

# ================== DATABASE ==================
def get_db():
    return sqlite3.connect("data.db", check_same_thread=False)

def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS names (name TEXT PRIMARY KEY, votes INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    db.commit()
    db.close()

init_db()

# ================== YORDAMCHI FUNKSIYALAR ==================
def is_member(user_id):
    try:
        status = bot.get_chat_member(CHANNEL, user_id).status
        return status in ["member", "administrator", "creator"]
    except:
        return False

def has_voted(user_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    r = cur.fetchone()
    db.close()
    return r is not None

def get_names():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT name, votes FROM names")
    data = cur.fetchall()
    db.close()
    return data

def results_text():
    data = get_names()
    total = sum(v for _, v in data)
    text = "📊 Ovoz berish natijalari:\n\n"
    for name, v in data:
        p = (v / total * 100) if total else 0
        bar = "🟩" * int(p // 10) + "⬜" * (10 - int(p // 10))
        text += f"👤 {name}: {v} ta ({p:.1f}%)\n{bar}\n\n"
    text += f"🧮 Jami ovozlar: {total}"
    return text

# ================== KLAVIATURALAR ==================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🗳 Ovoz berish")
    kb.add("➕ Ism qo‘shish", "🗑 Ism o‘chirish")
    return kb

def sub_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📢 Kanalga obuna bo‘lish",
                                      url=f"https://t.me/{CHANNEL.replace('@','')}"))
    kb.add(types.InlineKeyboardButton("✔ Obuna bo‘ldim", callback_data="check"))
    return kb

def vote_keyboard():
    kb = types.InlineKeyboardMarkup()
    for name, _ in get_names():
        kb.add(types.InlineKeyboardButton(f"🔥 {name}", callback_data=f"vote_{name}"))
    return kb

# ================== HOLATLAR ==================
add_mode = set()
del_mode = set()

# ================== HANDLERLAR ==================
@bot.message_handler(commands=["start"])
def start(message):
    if not is_member(message.from_user.id):
        bot.send_message(message.chat.id,
                         "❗ Ovoz berish uchun avval kanalga obuna bo‘ling:",
                         reply_markup=sub_keyboard())
    else:
        bot.send_message(message.chat.id,
                         "👋 Xush kelibsiz!",
                         reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🗳 Ovoz berish")
def vote(message):
    if not is_member(message.from_user.id):
        bot.send_message(message.chat.id,
                         "❗ Avval kanalga obuna bo‘ling:",
                         reply_markup=sub_keyboard())
        return

    if has_voted(message.from_user.id):
        bot.send_message(message.chat.id,
                         "❗ Siz allaqachon ovoz bergansiz.\n\n" + results_text())
    else:
        bot.send_message(message.chat.id,
                         "👇 Nomzod tanlang:",
                         reply_markup=vote_keyboard())

@bot.message_handler(func=lambda m: m.text == "➕ Ism qo‘shish")
def add_name(message):
    add_mode.add(message.chat.id)
    bot.send_message(message.chat.id, "✍️ Qo‘shiladigan ismni yozing:")

@bot.message_handler(func=lambda m: m.text == "🗑 Ism o‘chirish")
def del_name(message):
    del_mode.add(message.chat.id)
    bot.send_message(message.chat.id, "🗑 O‘chiriladigan ismni yozing:")

@bot.message_handler(func=lambda m: True)
def text_handler(message):
    if message.chat.id in add_mode:
        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT OR IGNORE INTO names (name) VALUES (?)", (message.text,))
        db.commit()
        db.close()
        add_mode.remove(message.chat.id)
        bot.send_message(message.chat.id, "✅ Ism qo‘shildi", reply_markup=main_menu())

    elif message.chat.id in del_mode:
        db = get_db()
        cur = db.cursor()
        cur.execute("DELETE FROM names WHERE name=?", (message.text,))
        db.commit()
        db.close()
        del_mode.remove(message.chat.id)
        bot.send_message(message.chat.id, "🗑 Ism o‘chirildi", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    if call.data == "check":
        if is_member(call.from_user.id):
            bot.send_message(call.message.chat.id,
                             "✔ Obuna tasdiqlandi",
                             reply_markup=main_menu())
        else:
            bot.answer_callback_query(call.id,
                                      "❌ Hali obuna emassiz",
                                      show_alert=True)

    elif call.data.startswith("vote_"):
        if has_voted(call.from_user.id):
            bot.answer_callback_query(call.id,
                                      "❗ Siz allaqachon ovoz bergansiz",
                                      show_alert=True)
            return

        name = call.data.split("_", 1)[1]
        db = get_db()
        cur = db.cursor()
        cur.execute("UPDATE names SET votes = votes + 1 WHERE name=?", (name,))
        cur.execute("INSERT INTO users (user_id) VALUES (?)", (call.from_user.id,))
        db.commit()
        db.close()

        bot.edit_message_text(results_text(),
                              call.message.chat.id,
                              call.message.message_id)

# ================== START ==================
bot.infinity_polling()
