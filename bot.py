#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات فوروارد گروه به کانال با وب‌هوک و پنل مدیریت (بدون مالک)
"""

import os
import json
import logging
import threading
from datetime import datetime
from flask import Flask, request, jsonify

# ---------- تنظیمات لاگ ----------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("=" * 60)
print("🤖 ربات فوروارد گروه به کانال")
print("🚀 نسخه: 2.1 بدون مالک (Admin Only)")
print("=" * 60)

# ---------- تنظیمات ----------
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
ADMIN_ID = 601668306  # اولین ادمین
DB_FILE = 'forward_db.json'
PORT = int(os.environ.get('PORT', 10000))

# ---------- Flask ----------
app = Flask(__name__)

# ---------- دیتابیس ----------
def load_db():
    default_db = {
        "admins": [ADMIN_ID],
        "source_groups": [],
        "forward_settings": {},
        "users": [],
        "stats": {
            "messages_forwarded": 0,
            "last_forward": None,
            "start_time": datetime.now().isoformat()
        }
    }

    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                default_db.update(json.load(f))
        except Exception as e:
            logger.error(e)

    return default_db


def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


db = load_db()

# ---------- دسترسی ----------
def is_admin(user_id):
    return user_id in db["admins"]

def is_authorized(user_id):
    return is_admin(user_id) or user_id in db["users"]

def update_stats():
    db["stats"]["messages_forwarded"] += 1
    db["stats"]["last_forward"] = datetime.now().isoformat()
    save_db(db)

# ---------- ربات ----------
class TelegramForwardBot:
    def __init__(self, token):
        import telebot
        self.telebot = telebot
        self.bot = telebot.TeleBot(token)
        self.types = telebot.types
        self.webhook_url = None
        self.setup_webhook()
        self.setup_handlers()

    def setup_webhook(self):
        base = os.environ.get('RENDER_EXTERNAL_URL') or os.environ.get('WEBHOOK_URL')
        if base:
            self.webhook_url = f"{base}/webhook"
            self.bot.remove_webhook()
            self.bot.set_webhook(url=self.webhook_url)

    def setup_handlers(self):

        @self.bot.message_handler(commands=['start'])
        def start(message):
            if not is_authorized(message.from_user.id):
                self.bot.reply_to(message, "❌ شما دسترسی ندارید.")
                return

            self.bot.reply_to(
                message,
                "🤖 ربات فوروارد فعال است",
                reply_markup=self.main_keyboard()
            )

        def main_keyboard():
            kb = self.types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("📊 وضعیت ربات", "🔧 تنظیم فوروارد")
            kb.add("➕ افزودن گروه", "🧪 تست فوروارد")
            return kb

        self.main_keyboard = main_keyboard

        @self.bot.message_handler(func=lambda m: m.text == "📊 وضعیت ربات")
        def status(message):
            self.bot.reply_to(
                message,
                f"""
📊 وضعیت ربات
• پیام‌های فوروارد شده: {db['stats']['messages_forwarded']}
• گروه‌ها: {len(db['source_groups'])}
• تنظیمات: {len(db['forward_settings'])}
                """
            )

        @self.bot.message_handler(func=lambda m: m.text == "➕ افزودن گروه")
        def add_group(message):
            if not is_admin(message.from_user.id):
                return
            msg = self.bot.reply_to(message, "🆔 آیدی گروه را ارسال کن:")
            self.bot.register_next_step_handler(msg, save_group)

        def save_group(message):
            gid = message.text.strip()
            if gid not in db["source_groups"]:
                db["source_groups"].append(gid)
                save_db(db)
                self.bot.reply_to(message, "✅ گروه اضافه شد")

        @self.bot.message_handler(
            content_types=['text', 'photo', 'video', 'document', 'audio', 'voice']
        )
        def forward(message):
            if message.chat.type not in ['group', 'supergroup']:
                return

            gid = f"@{message.chat.username}" if message.chat.username else str(message.chat.id)
            if gid not in db["forward_settings"]:
                return

            try:
                self.bot.forward_message(
                    db["forward_settings"][gid],
                    message.chat.id,
                    message.message_id
                )
                update_stats()
            except Exception as e:
                logger.error(e)

    def process_webhook(self, data):
        self.bot.process_new_updates(
            [self.telebot.types.Update.de_json(data)]
        )


bot_instance = TelegramForwardBot(TOKEN) if TOKEN else None

# ---------- Routes ----------
@app.route('/')
def home():
    return jsonify({"status": "online"})

@app.route('/webhook', methods=['POST'])
def webhook():
    if bot_instance:
        bot_instance.process_webhook(request.get_json())
    return jsonify({"ok": True})

# ---------- Run ----------
def run():
    app.run(host='0.0.0.0', port=PORT)

if __name__ == "__main__":
    run()
