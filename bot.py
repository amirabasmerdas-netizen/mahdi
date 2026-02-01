#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات فوروارد گروه به کانال با وب‌هوک و پنل مدیریت
"""

import os
import json
import logging
import threading
from datetime import datetime
from flask import Flask, request, jsonify

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("=" * 60)
print("🤖 ربات فوروارد گروه به کانال")
print("🚀 نسخه: 2.0 با وب‌هوک و پنل مدیریت")
print("=" * 60)

# ---------- تنظیمات ----------
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
ADMIN_ID = 8588773107  # آیدی مالک اصلی
DB_FILE = 'forward_db.json'
PORT = int(os.environ.get('PORT', 10000))

# ---------- Flask App ----------
app = Flask(__name__)

# ---------- دیتابیس ----------
def load_db():
    """بارگذاری دیتابیس"""
    default_db = {
        "owner_id": ADMIN_ID,
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
    
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                default_db.update(data)
    except Exception as e:
        logger.error(f"خطا در بارگذاری دیتابیس: {e}")
    
    return default_db

def save_db(data):
    """ذخیره دیتابیس"""
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"خطا در ذخیره دیتابیس: {e}")

# بارگذاری دیتابیس
db = load_db()

# ---------- توابع کمکی ----------
def is_owner(user_id):
    return user_id == db["owner_id"]

def is_admin(user_id):
    return user_id in db["admins"]

def is_authorized(user_id):
    return is_owner(user_id) or is_admin(user_id) or user_id in db["users"]

def update_stats():
    """به‌روزرسانی آمار"""
    db["stats"]["messages_forwarded"] += 1
    db["stats"]["last_forward"] = datetime.now().isoformat()
    save_db(db)

# ---------- ربات تلگرام ----------
class TelegramForwardBot:
    def __init__(self, token):
        self.token = token
        self.bot = None
        self.webhook_url = None
        self.init_bot()
    
    def init_bot(self):
        """مقداردهی اولیه ربات"""
        try:
            import telebot
            from telebot import types
            self.telebot = telebot
            self.types = types
            self.bot = telebot.TeleBot(self.token)
            logger.info("✅ کتابخانه telebot بارگذاری شد")
            
            # تنظیم وب‌هوک
            self.setup_webhook()
            
            # تنظیم هندلرها
            self.setup_handlers()
            
        except ImportError as e:
            logger.error(f"❌ خطا در بارگذاری کتابخانه: {e}")
    
    def setup_webhook(self):
        """تنظیم وب‌هوک"""
        try:
            # گرفتن آدرس وب‌هوک از متغیر محیطی
            webhook_url = os.environ.get('RENDER_EXTERNAL_URL') or os.environ.get('WEBHOOK_URL')
            if webhook_url:
                self.webhook_url = f"{webhook_url}/webhook"
                self.bot.remove_webhook()
                self.bot.set_webhook(url=self.webhook_url)
                logger.info(f"✅ وب‌هوک تنظیم شد: {self.webhook_url}")
            else:
                logger.warning("⚠️ آدرس وب‌هوک یافت نشد، از polling استفاده می‌کنم")
        except Exception as e:
            logger.error(f"❌ خطا در تنظیم وب‌هوک: {e}")
    
    def setup_handlers(self):
        """تنظیم هندلرهای ربات"""
        
        # ---------- دستور /start ----------
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            user_id = message.from_user.id
            
            if not is_authorized(user_id):
                self.bot.reply_to(
                    message,
                    "❌ شما دسترسی به این ربات را ندارید.\n"
                    "برای دریافت دسترسی با ادمین تماس بگیرید."
                )
                return
            
            welcome_text = f"""
👋 سلام {message.from_user.first_name}!

🤖 **ربات فوروارد گروه به کانال با وب‌هوک**

🔧 **امکانات:**
• فوروارد خودکار پیام‌ها
• پنل مدیریت پیشرفته
• اجرای 24/7 با وب‌هوک
• آمار دقیق عملکرد

📊 **آمار فعلی:**
• پیام‌های فوروارد شده: {db['stats']['messages_forwarded']}
• گروه‌های مبدا: {len(db['source_groups'])}
• تنظیمات فعال: {len(db['forward_settings'])}

🌐 **وضعیت سرور: آنلاین ✅**
            """
            
            self.bot.reply_to(
                message,
                welcome_text,
                reply_markup=self.create_main_keyboard(user_id)
            )
            logger.info(f"Start از کاربر {user_id}")
        
        # ---------- پنل اصلی ----------
        def create_main_keyboard(user_id):
            """ایجاد کیبورد اصلی"""
            markup = self.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            
            buttons = [
                "📊 وضعیت ربات",
                "📍 لیست گروه‌ها",
                "🎯 لیست کانال‌ها",
                "🔧 تنظیم فوروارد",
                "🧪 تست فوروارد",
                "📈 آمار کامل"
            ]
            
            if is_admin(user_id):
                buttons.extend([
                    "➕ افزودن گروه",
                    "➖ حذف گروه",
                    "➕ افزودن کانال",
                    "➖ حذف کانال"
                ])
            
            if is_owner(user_id):
                buttons.extend([
                    "👑 مدیریت ادمین‌ها",
                    "🔄 راه‌اندازی مجدد"
                ])
            
            for i in range(0, len(buttons), 2):
                if i + 1 < len(buttons):
                    markup.row(buttons[i], buttons[i + 1])
                else:
                    markup.add(buttons[i])
            
            return markup
        
        # ذخیره تابع برای استفاده در سایر هندلرها
        self.create_main_keyboard = create_main_keyboard
        
        # ---------- وضعیت ربات ----------
        @self.bot.message_handler(func=lambda m: m.text == "📊 وضعیت ربات")
        def handle_status(message):
            user_id = message.from_user.id
            
            if not is_authorized(user_id):
                return
            
            # محاسبه زمان فعالیت
            start_time = datetime.fromisoformat(db['stats']['start_time'])
            uptime = datetime.now() - start_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            status_text = f"""
📊 **وضعیت ربات**

🔄 **آمار عملکرد:**
• پیام‌های فوروارد شده: {db['stats']['messages_forwarded']}
• آخرین فوروارد: {db['stats']['last_forward'] or 'هنوز فورواردی نداشته'}
• زمان فعالیت: {days} روز، {hours} ساعت، {minutes} دقیقه

📁 **تنظیمات:**
• گروه‌های مبدا: {len(db['source_groups'])}
• تنظیمات فعال: {len(db['forward_settings'])}

🌐 **سرور:**
• وضعیت: آنلاین ✅
• پروتکل: وب‌هوک {'✅' if self.webhook_url else '❌'}
• پورت: {PORT}

💡 **نکته:** برای تنظیم از دکمه‌های زیر استفاده کنید
            """
            
            self.bot.reply_to(message, status_text)
        
        # ---------- آمار کامل ----------
        @self.bot.message_handler(func=lambda m: m.text == "📈 آمار کامل")
        def handle_full_stats(message):
            user_id = message.from_user.id
            
            if not is_admin(user_id):
                return
            
            stats_text = f"""
📈 **آمار کامل ربات**

👥 **کاربران:**
• مالک: {db['owner_id']}
• ادمین‌ها: {len(db['admins'])} نفر
• کاربران مجاز: {len(db['users'])} نفر

📊 **عملکرد:**
• کل پیام‌های فوروارد شده: {db['stats']['messages_forwarded']}
• زمان شروع: {db['stats']['start_time']}
• آخرین فعالیت: {db['stats']['last_forward'] or 'ندارد'}

🔧 **تنظیمات فعال:**
"""
            
            for group_id, channel_id in db['forward_settings'].items():
                stats_text += f"  • {group_id} → {channel_id}\n"
            
            if not db['forward_settings']:
                stats_text += "  • ❌ هیچ تنظیم فعالی وجود ندارد\n"
            
            stats_text += f"""
🌐 **اطلاعات سرور:**
• آدرس وب‌هوک: {self.webhook_url or 'ندارد'}
• پورت: {PORT}
• وضعیت: آنلاین
            """
            
            self.bot.reply_to(message, stats_text)
        
        # ---------- افزودن گروه ----------
        @self.bot.message_handler(func=lambda m: m.text == "➕ افزودن گروه")
        def handle_add_group(message):
            user_id = message.from_user.id
            
            if not is_admin(user_id):
                self.bot.reply_to(message, "❌ فقط ادمین‌ها می‌توانند گروه اضافه کنند.")
                return
            
            msg = self.bot.reply_to(
                message,
                "🔍 لطفا شناسه گروه را ارسال کنید:\n\n"
                "📌 **نکته:**\n"
                "1. ربات باید در گروه عضو باشد\n"
                "2. شناسه باید با @ یا -100 شروع شود\n\n"
                "مثال: @group_username\n"
                "یا: -1001234567890\n\n"
                "❌ برای لغو: /cancel"
            )
            self.bot.register_next_step_handler(msg, process_add_group)
        
        def process_add_group(message):
            if message.text == '/cancel':
                self.bot.reply_to(message, "❌ عملیات لغو شد.")
                return
            
            user_id = message.from_user.id
            group_id = message.text.strip()
            
            if not (group_id.startswith('@') or group_id.startswith('-100')):
                self.bot.reply_to(
                    message,
                    "❌ شناسه نامعتبر!\nشناسه باید با @ یا -100 شروع شود."
                )
                return
            
            if group_id in db['source_groups']:
                self.bot.reply_to(message, "⚠️ این گروه قبلاً اضافه شده است.")
                return
            
            try:
                chat = self.bot.get_chat(group_id)
                db['source_groups'].append(group_id)
                save_db(db)
                
                self.bot.reply_to(
                    message,
                    f"✅ گروه با موفقیت اضافه شد!\n\n"
                    f"🏷️ نام: {chat.title or 'بدون نام'}\n"
                    f"🆔 شناسه: `{group_id}`\n\n"
                    f"💡 حالا می‌توانید کانال مقصد را تنظیم کنید."
                )
                logger.info(f"گروه {group_id} توسط {user_id} اضافه شد")
                
            except Exception as e:
                self.bot.reply_to(
                    message,
                    f"❌ خطا در دسترسی به گروه:\n{str(e)[:100]}\n\n"
                    f"مطمئن شوید:\n"
                    f"1. ربات در گروه عضو است\n"
                    f"2. شناسه صحیح است"
                )
        
        # ---------- تنظیم فوروارد ----------
        @self.bot.message_handler(func=lambda m: m.text == "🔧 تنظیم فوروارد")
        def handle_set_forward(message):
            user_id = message.from_user.id
            
            if not is_admin(user_id):
                self.bot.reply_to(message, "❌ فقط ادمین‌ها می‌توانند تنظیم کنند.")
                return
            
            if not db['source_groups']:
                self.bot.reply_to(message, "❌ ابتدا باید گروه اضافه کنید.")
                return
            
            # ایجاد کیبورد اینلاین
            markup = self.types.InlineKeyboardMarkup()
            for group_id in db['source_groups']:
                current_channel = db['forward_settings'].get(group_id, '❌ تنظیم نشده')
                button_text = f"{group_id} → {current_channel}"
                callback_data = f"set:{group_id}"
                markup.add(self.types.InlineKeyboardButton(button_text, callback_data=callback_data))
            
            self.bot.reply_to(
                message,
                "🔍 **انتخاب گروه برای تنظیم فوروارد:**\n\n"
                "روی گروه مورد نظر کلیک کنید:",
                reply_markup=markup
            )
        
        # ---------- مدیریت callback ها ----------
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback(call):
            user_id = call.from_user.id
            
            if not is_admin(user_id):
                self.bot.answer_callback_query(call.id, "❌ دسترسی ندارید!")
                return
            
            if call.data.startswith('set:'):
                group_id = call.data.split(':')[1]
                
                msg = self.bot.send_message(
                    call.message.chat.id,
                    f"📌 **گروه انتخاب شده:** `{group_id}`\n\n"
                    "🔗 لطفا شناسه کانال مقصد را ارسال کنید:\n\n"
                    "📌 **نکته:**\n"
                    "1. ربات باید در کانال ادمین باشد\n"
                    "2. شناسه باید با @ یا -100 شروع شود\n\n"
                    "مثال: @channel_username\n"
                    "یا: -1001234567890\n\n"
                    "❌ برای لغو: /cancel"
                )
                self.bot.register_next_step_handler(msg, process_set_channel, group_id)
                self.bot.answer_callback_query(call.id)
        
        def process_set_channel(message, group_id):
            if message.text == '/cancel':
                self.bot.reply_to(message, "❌ تنظیم فوروارد لغو شد.")
                return
            
            channel_id = message.text.strip()
            
            if not (channel_id.startswith('@') or channel_id.startswith('-100')):
                self.bot.reply_to(
                    message,
                    "❌ شناسه نامعتبر!\nشناسه باید با @ یا -100 شروع شود."
                )
                return
            
            try:
                chat = self.bot.get_chat(channel_id)
                db['forward_settings'][group_id] = channel_id
                save_db(db)
                
                self.bot.reply_to(
                    message,
                    f"✅ تنظیم فوروارد با موفقیت ذخیره شد!\n\n"
                    f"📍 **مبدا:** `{group_id}`\n"
                    f"🎯 **مقصد:** `{channel_id}`\n\n"
                    f"🏷️ نام کانال: {chat.title or 'بدون نام'}\n\n"
                    f"💡 از این پس پیام‌های گروه به کانال فوروارد می‌شوند."
                )
                logger.info(f"تنظیم فوروارد: {group_id} → {channel_id}")
                
            except Exception as e:
                self.bot.reply_to(
                    message,
                    f"❌ خطا در دسترسی به کانال:\n{str(e)[:100]}\n\n"
                    f"مطمئن شوید:\n"
                    f"1. ربات در کانال ادمین است\n"
                    f"2. شناسه صحیح است"
                )
        
        # ---------- تست فوروارد ----------
        @self.bot.message_handler(func=lambda m: m.text == "🧪 تست فوروارد")
        def handle_test_forward(message):
            user_id = message.from_user.id
            
            if not is_authorized(user_id):
                return
            
            if not db['forward_settings']:
                self.bot.reply_to(message, "❌ ابتدا باید فوروارد را تنظیم کنید.")
                return
            
            try:
                self.bot.reply_to(message, "🔄 در حال ارسال پیام تست...")
                
                # ارسال پیام تست
                test_msg = self.bot.send_message(
                    message.chat.id,
                    f"""
🧪 **پیام تست فوروارد**
⏰ زمان: {datetime.now().strftime('%H:%M:%S')}
📅 تاریخ: {datetime.now().strftime('%Y-%m-%d')}
✅ ربات فعال و آماده است!
                    """
                )
                
                # فوروارد به اولین کانال مقصد
                first_channel = list(db['forward_settings'].values())[0]
                self.bot.forward_message(
                    first_channel,
                    message.chat.id,
                    test_msg.message_id
                )
                
                self.bot.reply_to(
                    message,
                    f"✅ تست موفقیت‌آمیز بود!\n"
                    f"پیام تست به `{first_channel}` فوروارد شد."
                )
                
            except Exception as e:
                self.bot.reply_to(
                    message,
                    f"❌ خطا در تست فوروارد:\n{str(e)[:150]}"
                )
        
        # ---------- راه‌اندازی مجدد ----------
        @self.bot.message_handler(func=lambda m: m.text == "🔄 راه‌اندازی مجدد")
        def handle_restart(message):
            user_id = message.from_user.id
            
            if not is_owner(user_id):
                self.bot.reply_to(message, "❌ فقط مالک می‌تواند ربات را راه‌اندازی مجدد کند.")
                return
            
            self.bot.reply_to(message, "🔄 در حال راه‌اندازی مجدد ربات...")
            
            try:
                # حذف و تنظیم مجدد وب‌هوک
                if self.webhook_url:
                    self.bot.remove_webhook()
                    self.bot.set_webhook(url=self.webhook_url)
                
                self.bot.reply_to(
                    message,
                    "✅ ربات با موفقیت راه‌اندازی مجدد شد!\n"
                    "🌐 وضعیت وب‌هوک: فعال"
                )
                logger.info(f"ربات توسط {user_id} راه‌اندازی مجدد شد")
                
            except Exception as e:
                self.bot.reply_to(message, f"❌ خطا در راه‌اندازی مجدد: {str(e)[:100]}")
        
        # ---------- فوروارد پیام‌ها ----------
        @self.bot.message_handler(
            func=lambda m: True,
            content_types=['text', 'photo', 'video', 'audio', 'voice', 'document', 'sticker', 'animation']
        )
        def forward_all_messages(message):
            """فوروارد تمام پیام‌ها از گروه‌های مبدا"""
            
            # فقط پیام‌های گروه
            if message.chat.type not in ['group', 'supergroup']:
                return
            
            # ساخت شناسه گروه
            if message.chat.username:
                group_id = f"@{message.chat.username}"
            else:
                group_id = str(message.chat.id)
            
            # بررسی اینکه گروه در لیست مبدا است
            if group_id not in db['source_groups'] and str(message.chat.id) not in db['source_groups']:
                return
            
            # یافتن کانال مقصد
            channel_id = None
            if group_id in db['forward_settings']:
                channel_id = db['forward_settings'][group_id]
            elif str(message.chat.id) in db['forward_settings']:
                channel_id = db['forward_settings'][str(message.chat.id)]
            
            if not channel_id:
                return
            
            # فوروارد پیام
            try:
                self.bot.forward_message(
                    channel_id,
                    message.chat.id,
                    message.message_id
                )
                
                # آپدیت آمار
                update_stats()
                logger.info(f"پیام فوروارد شد از {group_id} به {channel_id}")
                
            except Exception as e:
                logger.error(f"خطا در فوروارد پیام: {e}")
        
        logger.info("✅ هندلرهای ربات تنظیم شدند")
    
    def process_webhook_update(self, update):
        """پردازش بروزرسانی وب‌هوک"""
        if self.bot:
            self.bot.process_new_updates([self.telebot.types.Update.de_json(update)])
    
    def start_polling(self):
        """شروع polling (اگر وب‌هوک فعال نباشد)"""
        if self.bot and not self.webhook_url:
            logger.info("📡 شروع polling...")
            self.bot.infinity_polling()

# ایجاد نمونه ربات
bot_instance = None
if TOKEN:
    bot_instance = TelegramForwardBot(TOKEN)
else:
    logger.error("❌ توکن ربات یافت نشد!")

# ---------- Routes Flask ----------
@app.route('/')
def home():
    """صفحه اصلی"""
    return jsonify({
        'status': 'online',
        'service': 'Telegram Forward Bot',
        'version': '2.0',
        'stats': db['stats'],
        'config': {
            'groups': len(db['source_groups']),
            'channels': len(set(db['forward_settings'].values())),
            'webhook': bot_instance.webhook_url if bot_instance else None
        }
    })

@app.route('/health')
def health():
    """بررسی سلامت"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'bot_status': 'active' if bot_instance else 'inactive'
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """دریافت بروزرسانی‌های تلگرام"""
    if request.method == 'POST':
        try:
            update = request.get_json()
            logger.debug(f"دریافت وب‌هوک: {update}")
            
            if bot_instance:
                bot_instance.process_webhook_update(update)
            
            return jsonify({'status': 'ok'}), 200
        except Exception as e:
            logger.error(f"خطا در پردازش وب‌هوک: {e}")
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Method not allowed'}), 405

@app.route('/stats')
def stats():
    """آمار ربات"""
    return jsonify(db['stats'])

@app.route('/config')
def config():
    """تنظیمات"""
    return jsonify({
        'source_groups': db['source_groups'],
        'forward_settings': db['forward_settings'],
        'admins': db['admins'],
        'users': db['users']
    })

@app.route('/restart', methods=['POST'])
def restart():
    """راه‌اندازی مجدد ربات"""
    if bot_instance and bot_instance.webhook_url:
        try:
            bot_instance.bot.remove_webhook()
            bot_instance.bot.set_webhook(url=bot_instance.webhook_url)
            return jsonify({'status': 'restarted'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Webhook not configured'}), 400

# ---------- تابع اصلی ----------
def run_flask():
    """اجرای سرور Flask"""
    logger.info(f"🌐 سرور Flask در حال اجرا روی پورت {PORT}")
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=False,
        use_reloader=False
    )

def run_bot_polling():
    """اجرای ربات در حالت polling"""
    if bot_instance:
        bot_instance.start_polling()

if __name__ == "__main__":
    # چاپ اطلاعات
    print(f"✅ توکن: {TOKEN[:15]}..." if TOKEN else "❌ توکن یافت نشد")
    print(f"👑 مالک: {db['owner_id']}")
    print(f"🛠 ادمین‌ها: {len(db['admins'])} نفر")
    print(f"📍 گروه‌های مبدا: {len(db['source_groups'])} گروه")
    print(f"🎯 تنظیمات فوروارد: {len(db['forward_settings'])} تنظیم")
    print(f"🌐 وب‌هوک: {'فعال' if bot_instance and bot_instance.webhook_url else 'غیرفعال'}")
    print(f"🔧 پورت: {PORT}")
    print("=" * 60)
    
    # اگر وب‌هوک فعال است، فقط Flask را اجرا کن
    if bot_instance and bot_instance.webhook_url:
        print("🚀 ربات در حالت وب‌هوک اجرا می‌شود...")
        run_flask()
    else:
        print("🚀 ربات در حالت polling اجرا می‌شود...")
        # اجرای Flask در یک thread جداگانه
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # اجرای ربات در thread اصلی
        run_bot_polling()

