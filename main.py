#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات تلگرام برای فوروارد پیام‌ها از گروه به کانال
ورژن: 3.13
"""

import os
import json
import logging
import asyncio
import signal
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import sys

# کتابخانه‌های تلگرام
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackContext
)

# کتابخانه‌های وب برای وب‌هوک
from flask import Flask, request, jsonify, Response
import threading
from queue import Queue

# تنظیمات لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_forward.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# کلاس تنظیمات
@dataclass
class BotConfig:
    """کلاس ذخیره تنظیمات ربات"""
    source_group_id: str = ""          # شناسه گروه مبدا
    destination_channel_id: str = ""   # شناسه کانال مقصد (با @ یا -100)
    bot_token: str = ""                # توکن ربات تلگرام
    admin_id: str = ""                 # شناسه ادمین
    webhook_url: str = ""              # آدرس وب‌هوک
    forward_all: bool = True           # فوروارد تمام پیام‌ها
    forward_text: bool = True          # فوروارد متن
    forward_media: bool = True         # فوروارد مدیا
    forward_documents: bool = True     # فوروارد اسناد
    last_updated: str = ""             # تاریخ آخرین بروزرسانی
    
    def to_dict(self) -> Dict[str, Any]:
        """تبدیل به دیکشنری"""
        return asdict(self)
    
    def is_configured(self) -> bool:
        """بررسی کامل بودن تنظیمات"""
        return all([self.source_group_id, self.destination_channel_id, self.bot_token])
    
    def should_forward(self, message_type: str) -> bool:
        """بررسی آیا این نوع پیام باید فوروارد شود"""
        if not self.forward_all:
            return False
        
        if message_type == "text" and not self.forward_text:
            return False
        elif message_type in ["photo", "video", "audio", "voice"] and not self.forward_media:
            return False
        elif message_type in ["document", "sticker"] and not self.forward_documents:
            return False
        
        return True

# کلاس اصلی ربات
class TelegramGroupToChannelForwarder:
    """کلاس اصلی ربات فوروارد گروه به کانال"""
    
    def __init__(self):
        self.config = BotConfig()
        self.application: Optional[Application] = None
        self.bot: Optional[Bot] = None
        self.flask_app = Flask(__name__)
        self.message_queue = Queue()
        self.is_running = False
        self.setup_flask()
        self.load_config()
        
    def setup_flask(self):
        """تنظیم مسیرهای Flask برای وب‌هوک"""
        
        @self.flask_app.route('/')
        def home():
            """صفحه اصلی"""
            return jsonify({
                'status': 'online',
                'service': 'Telegram Group to Channel Forwarder',
                'version': '3.13',
                'time': datetime.now().isoformat(),
                'config_status': self.config.is_configured(),
                'endpoints': ['/', '/health', '/status', '/config', '/webhook']
            })
        
        @self.flask_app.route('/health')
        def health():
            """بررسی سلامت سرویس"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'bot_running': self.is_running
            })
        
        @self.flask_app.route('/status')
        def status():
            """وضعیت فعلی ربات"""
            return jsonify({
                'configured': self.config.is_configured(),
                'source_group': self.config.source_group_id,
                'destination_channel': self.config.destination_channel_id,
                'forward_all': self.config.forward_all,
                'has_token': bool(self.config.bot_token),
                'webhook_set': bool(self.config.webhook_url),
                'last_updated': self.config.last_updated,
                'queue_size': self.message_queue.qsize(),
                'bot_running': self.is_running
            })
        
        @self.flask_app.route('/config', methods=['GET', 'POST'])
        def handle_config():
            """مدیریت تنظیمات"""
            if request.method == 'GET':
                return jsonify(self.config.to_dict())
            elif request.method == 'POST':
                try:
                    data = request.json
                    if not data:
                        return jsonify({'error': 'داده‌ای ارسال نشده'}), 400
                    
                    # به‌روزرسانی تنظیمات
                    for key, value in data.items():
                        if hasattr(self.config, key):
                            setattr(self.config, key, value)
                    
                    self.config.last_updated = datetime.now().isoformat()
                    self.save_config()
                    
                    return jsonify({
                        'success': True,
                        'message': 'تنظیمات به‌روزرسانی شد',
                        'config': self.config.to_dict()
                    })
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
        
        @self.flask_app.route('/set_group/<group_id>')
        def set_group(group_id: str):
            """تنظیم گروه مبدا"""
            self.config.source_group_id = group_id
            self.save_config()
            return jsonify({
                'success': True,
                'message': f'گروه مبدا تنظیم شد: {group_id}'
            })
        
        @self.flask_app.route('/set_channel/<channel_id>')
        def set_channel(channel_id: str):
            """تنظیم کانال مقصد"""
            # بررسی فرمت کانال
            if not channel_id.startswith('@') and not channel_id.startswith('-100'):
                return jsonify({
                    'error': 'شناسه کانال باید با @ یا -100 شروع شود'
                }), 400
            
            self.config.destination_channel_id = channel_id
            self.save_config()
            return jsonify({
                'success': True,
                'message': f'کانال مقصد تنظیم شد: {channel_id}'
            })
        
        # مسیر وب‌هوک تلگرام
        @self.flask_app.route('/webhook', methods=['POST'])
        def webhook():
            """دریافت بروزرسانی‌های تلگرام"""
            if request.method == 'POST':
                update = Update.de_json(request.get_json(force=True), self.bot)
                
                # اضافه کردن به صف برای پردازش
                self.message_queue.put(update)
                
                return jsonify({'status': 'ok'}), 200
            
            return jsonify({'error': 'Method not allowed'}), 405
        
        @self.flask_app.errorhandler(404)
        def not_found(error):
            """مدیریت خطای 404"""
            return jsonify({'error': 'صفحه یافت نشد'}), 404
        
        @self.flask_app.errorhandler(500)
        def server_error(error):
            """مدیریت خطای 500"""
            return jsonify({'error': 'خطای سرور'}), 500
    
    def load_config(self):
        """بارگذاری تنظیمات"""
        config_loaded = False
        
        # اولویت: متغیرهای محیطی
        env_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if env_token:
            self.config.bot_token = env_token
            logger.info("توکن از متغیر محیطی بارگذاری شد")
            config_loaded = True
        
        # سپس فایل config.json
        if os.path.exists('config.json'):
            try:
                with open('config.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # به‌روزرسانی فقط مقادیر خالی
                    for key, value in data.items():
                        if hasattr(self.config, key) and not getattr(self.config, key):
                            setattr(self.config, key, value)
                    
                logger.info("تنظیمات از فایل بارگذاری شد")
                config_loaded = True
            except Exception as e:
                logger.error(f"خطا در خواندن فایل config: {e}")
        
        # آدرس وب‌هوک از متغیر محیطی
        webhook_url = os.environ.get('WEBHOOK_URL')
        if webhook_url:
            self.config.webhook_url = webhook_url
            logger.info(f"آدرس وب‌هوک تنظیم شد: {webhook_url}")
        
        # اگر هنوز توکن نداریم، خطا
        if not self.config.bot_token:
            logger.error("❌ توکن ربات یافت نشد!")
            logger.error("لطفا متغیر محیطی TELEGRAM_BOT_TOKEN را تنظیم کنید")
        
        return config_loaded
    
    def save_config(self):
        """ذخیره تنظیمات در فایل"""
        try:
            self.config.last_updated = datetime.now().isoformat()
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config.to_dict(), f, indent=4, ensure_ascii=False, ensure_ascii=False)
            logger.info("تنظیمات ذخیره شد")
        except Exception as e:
            logger.error(f"خطا در ذخیره تنظیمات: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        welcome_message = """
🤖 **ربات فوروارد گروه به کانال**

من پیام‌های یک گروه را به صورت خودکار به یک کانال فوروارد می‌کنم.

🔧 **دستورات مدیریتی:**
/setgroup - تنظیم گروه فعلی به عنوان مبدا
/setchannel - تنظیم کانال مقصد (شناسه کانال با @)
/settings - نمایش و تغییر تنظیمات
/status - وضعیت فعلی ربات
/help - راهنمای کامل

📝 **نکات مهم:**
1. ابتدا مرا به گروه و کانال اضافه کنید
2. در گروه دستور /setgroup را ارسال کنید
3. شناسه کانال را با /setchannel تنظیم کنید
4. ربات باید در کانال ادمین باشد

⚙️ **پیش‌فرض:** تمام پیام‌ها فوروارد می‌شوند
        """
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /help"""
        help_text = """
📚 **راهنمای کامل ربات**

🎯 **کاربرد:** فوروارد خودکار پیام‌ها از گروه به کانال

🔧 **دستورات:**
/setgroup - تنظیم گروه فعلی به عنوان مبدا
/setchannel @channel_id - تنظیم کانال مقصد
/settings - نمایش و تغییر تنظیمات فوروارد
/status - وضعیت ربات و آمار
/test - تست فوروارد یک پیام آزمایشی
/help - این راهنما

⚙️ **تنظیمات فوروارد:**
• متن 📝
• تصاویر 🖼️
• ویدیوها 🎥
• صوت 🎵
• اسناد 📎
• استیکرها 😄

🔐 **نیازمندی‌ها:**
1. ربات باید در گروه عضو باشد
2. ربات باید در کانال ادمین باشد
3. شناسه کانال باید با @ شروع شود

🌐 **وب‌هوک:** ربات از طریق وب‌هوک روی سرور Render همیشه فعال است
        """
        await update.message.reply_text(help_text)
    
    async def set_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /setgroup"""
        chat_id = str(update.effective_chat.id)
        chat_title = update.effective_chat.title or "این چت"
        
        # بررسی اینکه چت یک گروه است
        if update.effective_chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("❌ این دستور فقط در گروه‌ها قابل استفاده است!")
            return
        
        self.config.source_group_id = chat_id
        self.save_config()
        
        response = f"""
✅ **گروه مبدا تنظیم شد!**

📝 **جزئیات:**
• نام گروه: {chat_title}
• شناسه گروه: `{chat_id}`
• نوع: {update.effective_chat.type}

از این پس پیام‌های این گروه به کانال مقصد فوروارد می‌شوند.

➡️ **گام بعدی:** کانال مقصد را با دستور /setchannel تنظیم کنید.
        """
        
        await update.message.reply_text(response)
        logger.info(f"گروه مبدا تنظیم شد: {chat_id} ({chat_title})")
    
    async def set_channel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /setchannel"""
        if not context.args:
            await update.message.reply_text(
                "❌ لطفا شناسه کانال را وارد کنید.\n"
                "مثال: `/setchannel @mychannel`\n"
                "یا: `/setchannel -1001234567890`"
            )
            return
        
        channel_id = context.args[0].strip()
        
        # بررسی فرمت شناسه کانال
        if not (channel_id.startswith('@') or channel_id.startswith('-100')):
            await update.message.reply_text(
                "❌ فرمت شناسه کانال نامعتبر است!\n"
                "شناسه کانال باید:\n"
                "• با @ شروع شود (مثال: @mychannel)\n"
                "• یا با -100 شروع شود (شناسه عددی)"
            )
            return
        
        self.config.destination_channel_id = channel_id
        self.save_config()
        
        response = f"""
✅ **کانال مقصد تنظیم شد!**

📝 **جزئیات:**
• شناسه کانال: `{channel_id}`

پیام‌های گروه مبدا به این کانال فوروارد خواهند شد.

⚠️ **توجه:** اطمینان حاصل کنید که ربات در این کانال ادمین است.
        """
        
        await update.message.reply_text(response)
        logger.info(f"کانال مقصد تنظیم شد: {channel_id}")
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /settings"""
        if context.args:
            # تغییر تنظیمات
            try:
                setting = context.args[0].lower()
                value = context.args[1].lower() if len(context.args) > 1 else None
                
                if setting == "text":
                    self.config.forward_text = value != "off"
                    await update.message.reply_text(
                        f"✅ فوروارد متن {'فعال' if self.config.forward_text else 'غیرفعال'} شد"
                    )
                elif setting == "media":
                    self.config.forward_media = value != "off"
                    await update.message.reply_text(
                        f"✅ فوروارد مدیا {'فعال' if self.config.forward_media else 'غیرفعال'} شد"
                    )
                elif setting == "documents":
                    self.config.forward_documents = value != "off"
                    await update.message.reply_text(
                        f"✅ فوروارد اسناد {'فعال' if self.config.forward_documents else 'غیرفعال'} شد"
                    )
                elif setting == "all":
                    self.config.forward_all = value != "off"
                    await update.message.reply_text(
                        f"✅ فوروارد تمام پیام‌ها {'فعال' if self.config.forward_all else 'غیرفعال'} شد"
                    )
                else:
                    await update.message.reply_text(
                        "❌ تنظیم نامعتبر\n"
                        "تنظیمات مجاز: text, media, documents, all\n"
                        "مثال: `/settings text off`"
                    )
                    return
                
                self.save_config()
                
            except Exception as e:
                await update.message.reply_text(f"❌ خطا در تغییر تنظیمات: {str(e)}")
        else:
            # نمایش تنظیمات فعلی
            settings_text = f"""
⚙️ **تنظیمات فعلی فوروارد**

{'✅' if self.config.forward_all else '❌'} **همه پیام‌ها:** {'فعال' if self.config.forward_all else 'غیرفعال'}
{'✅' if self.config.forward_text else '❌'} **متن:** {'فعال' if self.config.forward_text else 'غیرفعال'}
{'✅' if self.config.forward_media else '❌'} **مدیا (عکس، ویدیو، صوت):** {'فعال' if self.config.forward_media else 'غیرفعال'}
{'✅' if self.config.forward_documents else '❌'} **اسناد و استیکر:** {'فعال' if self.config.forward_documents else 'غیرفعال'}

📝 **نحوه تغییر:**
`/settings text on/off` - فعال/غیرفعال کردن فوروارد متن
`/settings media on/off` - فعال/غیرفعال کردن فوروارد مدیا
`/settings documents on/off` - فعال/غیرفعال کردن فوروارد اسناد
`/settings all on/off` - فعال/غیرفعال کردن همه پیام‌ها

مثال: `/settings media off`
            """
            
            await update.message.reply_text(settings_text)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /status"""
        status_emoji = "✅" if self.config.is_configured() else "⚠️"
        
        # آمار فوروارد از context
        forwarded_count = context.bot_data.get('forwarded_count', 0)
        
        status_text = f"""
{status_emoji} **وضعیت ربات**

📊 **آمار:**
• پیام‌های فوروارد شده: {forwarded_count}
• پیام‌های در صف: {self.message_queue.qsize()}

📍 **گروه مبدا:**
{'`' + self.config.source_group_id + '`' if self.config.source_group_id else '❌ تنظیم نشده'}

🎯 **کانال مقصد:**
{'`' + self.config.destination_channel_id + '`' if self.config.destination_channel_id else '❌ تنظیم نشده'}

⚙️ **تنظیمات فوروارد:**
• همه پیام‌ها: {'✅' if self.config.forward_all else '❌'}
• متن: {'✅' if self.config.forward_text else '❌'}
• مدیا: {'✅' if self.config.forward_media else '❌'}
• اسناد: {'✅' if self.config.forward_documents else '❌'}

🌐 **وب‌هوک:** {'✅ فعال' if self.config.webhook_url else '❌ غیرفعال'}

💡 **وضعیت کلی:**
{'✅ آماده به کار' if self.config.is_configured() else '⚠️ نیاز به تنظیم'}
        """
        
        await update.message.reply_text(status_text)
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /test - تست فوروارد"""
        if not self.config.is_configured():
            await update.message.reply_text("❌ ربات هنوز تنظیم نشده است!")
            return
        
        try:
            # ارسال پیام تست
            test_message = f"""
🔧 **تست فوروارد ربات**
🕒 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
✅ اگر این پیام را می‌بینید، ربات به درستی کار می‌کند.

گروه مبدا: {self.config.source_group_id}
کانال مقصد: {self.config.destination_channel_id}
            """
            
            await update.message.reply_text("در حال تست فوروارد...")
            
            # فوروارد پیام تست
            await update.message.forward(
                chat_id=self.config.destination_channel_id
            )
            
            await update.message.reply_text("✅ تست موفقیت‌آمیز بود!")
            logger.info("تست فوروارد انجام شد")
            
        except Exception as e:
            error_msg = f"❌ خطا در تست فوروارد: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(error_msg)
    
    def get_message_type(self, update: Update) -> str:
        """تشخیص نوع پیام"""
        if update.message:
            if update.message.text:
                return "text"
            elif update.message.photo:
                return "photo"
            elif update.message.video:
                return "video"
            elif update.message.audio:
                return "audio"
            elif update.message.voice:
                return "voice"
            elif update.message.document:
                return "document"
            elif update.message.sticker:
                return "sticker"
        
        return "unknown"
    
    async def forward_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """فوروارد تمام پیام‌ها از گروه به کانال"""
        # بررسی تنظیمات
        if not self.config.is_configured():
            return
        
        # بررسی اینکه پیام از گروه مبدا است
        current_chat_id = str(update.effective_chat.id)
        
        if current_chat_id != self.config.source_group_id:
            return
        
        # تشخیص نوع پیام
        message_type = self.get_message_type(update)
        
        # بررسی آیا این نوع پیام باید فوروارد شود
        if not self.config.should_forward(message_type):
            logger.debug(f"پیام نوع {message_type} فوروارد نمی‌شود (تنظیمات)")
            return
        
        try:
            # فوروارد پیام به کانال
            await update.message.forward(
                chat_id=self.config.destination_channel_id
            )
            
            # آپدیت آمار
            if 'forwarded_count' not in context.bot_data:
                context.bot_data['forwarded_count'] = 0
            context.bot_data['forwarded_count'] += 1
            
            # لاگ‌گیری
            logger.info(
                f"پیام فوروارد شد از {current_chat_id} به {self.config.destination_channel_id} | "
                f"نوع: {message_type} | کل: {context.bot_data['forwarded_count']}"
            )
            
        except Exception as e:
            logger.error(f"خطا در فوروارد پیام نوع {message_type}: {e}")
            
            # اطلاع به ادمین در صورت خطای دسترسی
            if "Forbidden" in str(e) or "Chat not found" in str(e):
                try:
                    if self.config.admin_id:
                        await context.bot.send_message(
                            chat_id=self.config.admin_id,
                            text=f"⚠️ خطا در فوروارد پیام به کانال {self.config.destination_channel_id}\n"
                                 f"خطا: {str(e)[:100]}"
                        )
                except:
                    pass
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت خطاهای ربات"""
        logger.error(f"خطا در پردازش بروزرسانی: {context.error}", exc_info=True)
        
        # در صورت خطای توکن نامعتبر
        if "Unauthorized" in str(context.error):
            logger.critical("توکن ربات نامعتبر است! لطفا توکن جدیدی دریافت کنید.")
    
    def setup_handlers(self, application: Application):
        """تنظیم هندلرهای ربات تلگرام"""
        # هندلر دستورات
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("setgroup", self.set_group_command))
        application.add_handler(CommandHandler("setchannel", self.set_channel_command))
        application.add_handler(CommandHandler("settings", self.settings_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("test", self.test_command))
        
        # هندلر پیام‌ها (فوروارد همه)
        application.add_handler(
            MessageHandler(
                filters.ALL & ~filters.COMMAND,
                self.forward_all_messages
            )
        )
        
        # هندلر خطا
        application.add_error_handler(self.error_handler)
    
    def run_flask(self, port: int = 8080):
        """اجرای سرور Flask"""
        try:
            logger.info(f"🌐 سرور Flask در حال اجرا روی پورت {port}")
            logger.info(f"🔗 آدرس وب‌هوک: {self.config.webhook_url}/webhook")
            
            self.flask_app.run(
                host='0.0.0.0',
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            logger.error(f"خطا در اجرای Flask: {e}")
    
    async def setup_webhook(self):
        """تنظیم وب‌هوک برای تلگرام"""
        if not self.config.webhook_url:
            logger.warning("آدرس وب‌هوک تنظیم نشده، از polling استفاده می‌کنم")
            return False
        
        try:
            webhook_url = f"{self.config.webhook_url}/webhook"
            
            # حذف وب‌هوک قبلی
            await self.bot.delete_webhook()
            
            # تنظیم وب‌هوک جدید
            await self.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
            logger.info(f"✅ وب‌هوک تنظیم شد: {webhook_url}")
            return True
            
        except Exception as e:
            logger.error(f"خطا در تنظیم وب‌هوک: {e}")
            return False
    
    async def run_telegram_bot(self):
        """اجرای ربات تلگرام"""
        try:
            # بررسی توکن
            if not self.config.bot_token:
                logger.error("❌ توکن ربات تنظیم نشده است!")
                logger.error("لطفا متغیر محیطی TELEGRAM_BOT_TOKEN را تنظیم کنید")
                return
            
            logger.info("در حال راه‌اندازی ربات تلگرام...")
            
            # ایجاد Application
            self.application = (
                Application.builder()
                .token(self.config.bot_token)
                .build()
            )
            
            # گرفتن شیء bot
            self.bot = self.application.bot
            
            # تنظیم هندلرها
            self.setup_handlers(self.application)
            
            # اطلاعات ربات
            bot_info = await self.bot.get_me()
            logger.info(f"✅ ربات تلگرام آماده است!")
            logger.info(f"🤖 نام ربات: {bot_info.first_name}")
            logger.info(f"📝 نام کاربری: @{bot_info.username}")
            
            # تنظیم وب‌هوک
            webhook_set = await self.setup_webhook()
            
            if webhook_set:
                # در حالت وب‌هوک، فقط Flask را اجرا می‌کنیم
                logger.info("🔄 ربات در حالت وب‌هوک اجرا می‌شود...")
                self.is_running = True
                
                # نگه داشتن برنامه فعال
                while self.is_running:
                    await asyncio.sleep(1)
                    
            else:
                # حالت fallback: polling
                logger.info("🔄 ربات در حالت polling اجرا می‌شود...")
                await self.application.initialize()
                await self.application.start()
                
                self.is_running = True
                
                # شروع polling
                await self.application.updater.start_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True
                )
                
                # نگه داشتن ربات فعال
                await asyncio.Event().wait()
                
        except asyncio.CancelledError:
            logger.info("ربات متوقف شد")
        except Exception as e:
            logger.error(f"خطای بحرانی در اجرای ربات: {e}", exc_info=True)
            raise
        finally:
            self.is_running = False
            if self.application:
                await self.application.stop()
                await self.application.shutdown()
    
    def run(self):
        """اجرای همزمان Flask و Telegram Bot"""
        # گرفتن پورت از متغیر محیطی
        port = int(os.environ.get('PORT', 8080))
        
        # تنظیم آدرس وب‌هوک اگر در Render هستیم
        if not self.config.webhook_url:
            render_url = os.environ.get('RENDER_EXTERNAL_URL')
            if render_url:
                self.config.webhook_url = render_url
                logger.info(f"آدرس وب‌هوک از Render تنظیم شد: {render_url}")
                self.save_config()
        
        # اجرای Flask در thread جداگانه
        flask_thread = threading.Thread(
            target=self.run_flask,
            args=(port,),
            daemon=True
        )
        flask_thread.start()
        
        logger.info(f"🌐 وب سرور در حال اجرا روی پورت {port}")
        logger.info(f"🔗 آدرس سلامت: http://localhost:{port}/health")
        logger.info(f"📊 وضعیت: http://localhost:{port}/status")
        
        # اجرای ربات تلگرام در event loop اصلی
        try:
            asyncio.run(self.run_telegram_bot())
        except KeyboardInterrupt:
            logger.info("ربات متوقف شد")
            self.is_running = False
        except Exception as e:
            logger.error(f"خطا در اجرای ربات: {e}")
            self.is_running = False
    
    def stop(self):
        """متوقف کردن ربات"""
        self.is_running = False
        logger.info("در حال توقف ربات...")

# تابع اصلی
def main():
    """تابع اصلی اجرای برنامه"""
    print("=" * 60)
    print("🤖 ربات تلگرام فوروارد گروه به کانال")
    print(f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 پایتون: {sys.version.split()[0]}")
    print(f"🌐 حالت: Webhook + Flask")
    print("=" * 60)
    
    # ثبت handler برای خاتمه
    def signal_handler(signum, frame):
        print("\n👋 در حال خاتمه ربات...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # ایجاد و اجرای ربات
    bot = TelegramGroupToChannelForwarder()
    bot.run()

if __name__ == "__main__":
    main()
