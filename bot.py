#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
import telebot

# ---------------- CONFIG ----------------
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
DB_FILE = "forward_db.json"

# ادمین‌ها (مالک نداریم)
DEFAULT_ADMINS = [601668306, 8588773170]

# ---------------- LOG ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ForwardBot")

# ---------------- DB ----------------
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "admins": DEFAULT_ADMINS,
        "forward_map": {},  # group_id(str) -> channel_id(str)
        "stats": {
            "forwarded": 0,
            "start_time": datetime.now().isoformat()
        }
    }

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

db = load_db()

# اگر دیتابیس قدیمیه، ادمین‌ها رو سینک کن
for aid in DEFAULT_ADMINS:
    if aid not in db["admins"]:
        db["admins"].append(aid)
save_db()

# ---------------- ACCESS ----------------
def is_admin(uid):
    return uid in db["admins"]

# ---------------- BOT ----------------
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ---------------- KEYBOARD ----------------
def admin_kb():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ افزودن فوروارد")
    kb.add("📊 وضعیت")
    return kb

# ---------------- COMMANDS ----------------
@bot.message_handler(commands=["start"])
def start(m):
    if not is_admin(m.from_user.id):
        bot.reply_to(m, "❌ شما ادمین این ربات نیستید.")
        return
    bot.reply_to(
        m,
        "✅ ربات فوروارد فعال است\n\n"
        "از دکمه‌ها استفاده کن 👇",
        reply_markup=admin_kb()
    )

# ---------------- STATUS ----------------
@bot.message_handler(func=lambda m: m.text == "📊 وضعیت")
def status(m):
    if not is_admin(m.from_user.id):
        return
    bot.reply_to(
        m,
        f"""
📊 <b>وضعیت ربات</b>

• فوروارد شده: {db['stats']['forwarded']}
• تنظیمات فعال: {len(db['forward_map'])}
• ادمین‌ها: {len(db['admins'])}
        """
    )

# ---------------- ADD FORWARD ----------------
@bot.message_handler(func=lambda m: m.text == "➕ افزودن فوروارد")
def ask_forward(m):
    if not is_admin(m.from_user.id):
        return
    msg = bot.reply_to(
        m,
        "🆔 آیدی <b>گروه</b> را بفرست (عدد -100...):"
    )
    bot.register_next_step_handler(msg, ask_channel)

def ask_channel(m):
    if not m.text.startswith("-100"):
        bot.reply_to(m, "❌ آیدی گروه نامعتبره")
        return
    group_id = m.text.strip()

    msg = bot.reply_to(
        m,
        "🆔 آیدی <b>کانال مقصد</b> را بفرست (عدد -100...):"
    )
    bot.register_next_step_handler(msg, save_forward, group_id)

def save_forward(m, group_id):
    if not m.text.startswith("-100"):
        bot.reply_to(m, "❌ آیدی کانال نامعتبره")
        return

    channel_id = m.text.strip()
    db["forward_map"][group_id] = channel_id
    save_db()

    bot.reply_to(
        m,
        f"✅ فوروارد تنظیم شد:\n\n"
        f"{group_id} ➜ {channel_id}"
    )

# ---------------- FORWARD ----------------
@bot.message_handler(
    content_types=[
        "text", "photo", "video", "document",
        "audio", "voice", "sticker", "animation"
    ]
)
def forward_all(m):
    if m.chat.type not in ["group", "supergroup"]:
        return

    gid = str(m.chat.id)
    if gid not in db["forward_map"]:
        return

    try:
        bot.forward_message(
            db["forward_map"][gid],
            m.chat.id,
            m.message_id
        )
        db["stats"]["forwarded"] += 1
        save_db()
    except Exception as e:
        logger.error(e)

# ---------------- WEBHOOK ----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    bot.process_new_updates(
        [telebot.types.Update.de_json(update)]
    )
    return jsonify(ok=True)

@app.route("/")
def home():
    return jsonify(status="online")

# ---------------- RUN ----------------
if __name__ == "__main__":
    webhook_url = os.environ.get("RENDER_EXTERNAL_URL")
    if webhook_url:
        bot.remove_webhook()
        bot.set_webhook(f"{webhook_url}/webhook")
    app.run(host="0.0.0.0", port=PORT)
