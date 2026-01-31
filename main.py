#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات تلگرام برای فوروارد پیام از گروه مبدا به مقصد
ورژن: 3.13
تاریخ: 2024
"""

import os
import json
import logging
import asyncio
from typing import Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# کتابخانه‌های تلگرام
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# کتابخانه‌های وب
from flask import Flask, request, jsonify
import threading

# تنظیمات لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# کلاس تنظیمات
@dataclass
class BotConfig:
    """کلاس ذخیره تنظیمات ربات"""
    source_chat_id: str = ""          # شناسه گروه مبدا
    destination_chat_id: str = ""     # شناسه گروه مقصد
    bot_token: str = ""               # توکن ربات تلگرام
    admin_id: str = ""                # شناسه ادمین (اختیاری)
    last_updated: str = ""            # تاریخ آخرین بروزرسانی
    
    def to_dict(self):
        """تبدیل به دیکشنری"""
        return asdict(self)
    
    def is_configured(self) -> bool:
        """بررسی کامل بودن تنظیمات"""
        return all([self.source_chat_id, self.destination_chat_id, self.bot_token])

# کلاس اصلی ربات
class TelegramForwardBot:
    """کلاس اصلی ربات فوروارد پیام"""
    
    def __init__(self):
        self.config = BotConfig()
        self.application: Optional[Application] = None
        self.flask_app = Flask(__name__)
        self.setup_flask()
        self.load_config()
        
    def setup_flask(self):
        """تنظیم مسیرهای Flask"""
        
        @self.flask_app.route('/')
        def home():
            """صفحه اصلی"""
            return jsonify({
                'status': 'online',
                'service': 'Telegram Forward Bot',
                'version': '3.13',
                'endpoints': ['/', '/health', '/status', '/config', '/set_source/<chat_id>', '/set_dest/<chat_id>']
            })
        
        @self.flask_app.route('/health')
        def health():
            """بررسی سلامت سرویس"""
            return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
        
        @self.flask_app.route('/status')
        def status():
            """وضعیت فعلی ربات"""
            return jsonify({
                'configured': self.config.is_configured(),
                'source_chat': self.config.source_chat_id,
                'destination_chat': self.config.destination_chat_id,
                'last_updated': self.config.last_updated
            })
        
        @self.flask_app.route('/config')
        def get_config():
            """دریافت تنظیمات"""
            return jsonify(self.config.to_dict())
        
        @self.flask_app.route('/set_source/<chat_id>')
        def set_source(chat_id: str):
            """تنظیم گروه مبدا از طریق وب"""
            self.config.source_chat_id = chat_id
            self.config.last_updated = datetime.now().isoformat()
            self.save_config()
            return jsonify({
                'success': True,
                'message': f'گروه مبدا تنظیم شد: {chat_id}'
            })
        
        @self.flask_app.route('/set_dest/<chat_id>')
        def set_destination(chat_id: str):
            """تنظیم گروه مقصد از طریق وب"""
            self.config.destination_chat_id = chat_id
            self.config.last_updated = datetime.now().isoformat()
            self.save_config()
            return jsonify({
                'success': True,
                'message': f'گروه مقصد تنظیم شد: {chat_id}'
            })
        
        @self.flask_app.errorhandler(404)
        def not_found(error):
            """مدیریت خطای 404"""
            return jsonify({'error': 'صفحه یافت نشد'}), 404
    
    def load_config(self):
        """بارگذاری تنظیمات از فایل یا متغیرهای محیطی"""
        try:
            # اولویت ۱: فایل config.json
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config = BotConfig(**data)
                logger.info("تنظیمات از فایل بارگذاری شد")
            
            # اولویت ۲: متغیرهای محیطی
            env_token = os.environ.get('TELEGRAM_BOT_TOKEN')
            if env_token:
                self.config.bot_token = env_token
                logger.info("توکن از متغیر محیطی بارگذاری شد")
            
            # اگر هنوز توکن نداریم، از فایل config_sample.json استفاده کن
            if not self.config.bot_token and os.path.exists('config_sample.json'):
                with open('config_sample.json', 'r', encoding='utf-8') as f:
                    sample_data = json.load(f)
                    self.config.bot_token = sample_data.get('bot_token', '')
            
            # اگر هنوز هم توکن نداریم، لاگ خطا
            if not self.config.bot_token:
                logger.warning("توکن ربات یافت نشد. لطفا توکن را تنظیم کنید.")
                
        except Exception as e:
            logger.error(f"خطا در بارگذاری تنظیمات: {e}")
    
    def save_config(self):
        """ذخیره تنظیمات در فایل"""
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config.to_dict(), f, indent=4, ensure_ascii=False)
            logger.info("تنظیمات ذخیره شد")
        except Exception as e:
            logger.error(f"خطا در ذخیره تنظیمات: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        user = update.effective_user
        welcome_message = """
👋 سلام! من ربات فوروارد پیام هستم.

🔧 **دستورات اصلی:**
/set_source - تنظیم این گروه به عنوان مبدا
/set_destination - تنظیم این گروه به عنوان مقصد
/show - نمایش تنظیمات فعلی
/help - راهنمای کامل

📝 **نحوه استفاده:**
1. مرا به گروه‌های مورد نظر اضافه کنید
2. در گروه مبدا دستور /set_source را بفرستید
3. در گروه مقصد دستور /set_destination را بفرستید
4. از این پس تمام پیام‌های گروه مبدا به گروه مقصد فوروارد می‌شوند
        """
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /help"""
        help_text = """
📚 **راهنمای ربات فوروارد پیام**

🎯 **هدف:**
فوروارد خودکار پیام‌ها از یک گروه (مبدا) به گروه دیگر (مقصد)

🔧 **دستورات:**
/set_source - تنظیم گروه فعلی به عنوان مبدا
/set_destination - تنظیم گروه فعلی به عنوان مقصد
/show - نمایش تنظیمات فعلی
/status - وضعیت ربات
/help - این راهنما

⚙️ **نحوه تنظیم:**
1. مرا به هر دو گروه اضافه کنید
2. در گروه مبدا: /set_source
3. در گروه مقصد: /set_destination

⚠️ **نکات مهم:**
• برای تنظیم گروه، دستور را در همان گروه ارسال کنید
• ربات باید در هر دو گروه عضو باشد
• پیام‌های فوروارد شده با نام کاربری اصلی ارسال می‌شوند
• ربات روی سرور Render همیشه فعال است
        """
        await update.message.reply_text(help_text)
    
    async def set_source_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /set_source"""
        chat_id = str(update.effective_chat.id)
        chat_title = update.effective_chat.title or "این چت"
        
        self.config.source_chat_id = chat_id
        self.config.last_updated = datetime.now().isoformat()
        self.save_config()
        
        response = f"""
✅ **گروه مبدا تنظیم شد!**

📝 **جزئیات:**
• نام گروه: {chat_title}
• شناسه گروه: `{chat_id}`

از این پس تمام پیام‌های این گروه به گروه مقصد فوروارد خواهند شد.
برای تنظیم گروه مقصد از دستور /set_destination استفاده کنید.
        """
        
        await update.message.reply_text(response)
        logger.info(f"گروه مبدا تنظیم شد: {chat_id} ({chat_title})")
    
    async def set_destination_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /set_destination"""
        chat_id = str(update.effective_chat.id)
        chat_title = update.effective_chat.title or "این چت"
        
        self.config.destination_chat_id = chat_id
        self.config.last_updated = datetime.now().isoformat()
        self.save_config()
        
        response = f"""
✅ **گروه مقصد تنظیم شد!**

📝 **جزئیات:**
• نام گروه: {chat_title}
• شناسه گروه: `{chat_id}`

پیام‌های گروه مبدا به این گروه فوروارد خواهند شد.
برای تنظیم گروه مبدا از دستور /set_source استفاده کنید.
        """
        
        await update.message.reply_text(response)
        logger.info(f"گروه مقصد تنظیم شد: {chat_id} ({chat_title})")
    
    async def show_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /show"""
        if not self.config.is_configured():
            await update.message.reply_text("⚠️ ربات هنوز به طور کامل تنظیم نشده است.")
            return
        
        status_text = f"""
📊 **تنظیمات فعلی ربات:**

📍 **گروه مبدا:**
• شناسه: `{self.config.source_chat_id}`
• وضعیت: {'✅ تنظیم شده' if self.config.source_chat_id else '❌ تنظیم نشده'}

🎯 **گروه مقصد:**
• شناسه: `{self.config.destination_chat_id}`
• وضعیت: {'✅ تنظیم شده' if self.config.destination_chat_id else '❌ تنظیم نشده'}

🕒 **آخرین بروزرسانی:**
{self.config.last_updated}

🔧 **وضعیت کلی:**
{'✅ آماده به کار' if self.config.is_configured() else '⚠️ نیاز به تنظیم'}
        """
        
        await update.message.reply_text(status_text)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /status"""
        status_emoji = "🟢" if self.config.is_configured() else "🟡"
        
        status_text = f"""
{status_emoji} **وضعیت ربات**

🔑 **توکن ربات:** {'✅ تنظیم شده' if self.config.bot_token else '❌ تنظیم نشده'}
📤 **گروه مبدا:** {'✅ تنظیم شده' if self.config.source_chat_id else '❌ تنظیم نشده'}
📥 **گروه مقصد:** {'✅ تنظیم شده' if self.config.destination_chat_id else '❌ تنظیم نشده'}

🖥 **سرور:** Render
📡 **پروتکل:** Webhook
⏰ **آخرین بروزرسانی:** {self.config.last_updated or 'نامشخص'}

💡 **نکته:** برای تنظیم کامل، هم گروه مبدا و هم مقصد باید تنظیم شوند.
        """
        
        await update.message.reply_text(status_text)
    
    async def forward_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """فوروارد پیام از مبدا به مقصد"""
        # بررسی تنظیمات
        if not self.config.is_configured():
            return
        
        # بررسی اینکه پیام از گروه مبدا است
        current_chat_id = str(update.effective_chat.id)
        
        if current_chat_id != self.config.source_chat_id:
            return
        
        # بررسی وجود گروه مقصد
        if not self.config.destination_chat_id:
            return
        
        try:
            # فوروارد پیام
            await update.message.forward(
                chat_id=self.config.destination_chat_id,
                message_thread_id=None
            )
            
            # لاگ‌گیری
            logger.info(
                f"پیام فوروارد شد از {current_chat_id} به {self.config.destination_chat_id} | "
                f"نوع پیام: {update.message.content_type if update.message else 'unknown'}"
            )
            
        except Exception as e:
            logger.error(f"خطا در فوروارد پیام: {e}")
            
            # در صورت خطای دسترسی، اطلاع به ادمین
            if "Forbidden" in str(e) or "Chat not found" in str(e):
                try:
                    await update.message.reply_text(
                        "⚠️ خطا در فوروارد پیام. "
                        "ممکن است ربات از گروه مقصد حذف شده باشد."
                    )
                except:
                    pass
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت خطاهای ربات"""
        logger.error(f"خطا در پردازش بروزرسانی: {context.error}")
        
        # در صورت خطای توکن نامعتبر
        if "Unauthorized" in str(context.error):
            logger.critical("توکن ربات نامعتبر است! لطفا توکن جدیدی دریافت کنید.")
    
    def setup_handlers(self):
        """تنظیم هندلرهای ربات تلگرام"""
        if not self.application:
            return
        
        # هندلر دستورات
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("set_source", self.set_source_command))
        self.application.add_handler(CommandHandler("set_destination", self.set_destination_command))
        self.application.add_handler(CommandHandler("show", self.show_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # هندلر پیام‌ها (فوروارد)
        self.application.add_handler(
            MessageHandler(
                filters.ALL & ~filters.COMMAND,
                self.forward_message
            )
        )
        
        # هندلر خطا
        self.application.add_error_handler(self.error_handler)
    
    def run_flask(self, port: int = 8080):
        """اجرای سرور Flask"""
        try:
            logger.info(f"سرور Flask در حال اجرا روی پورت {port}")
            self.flask_app.run(
                host='0.0.0.0',
                port=port,
                debug=False,
                use_reloader=False
            )
        except Exception as e:
            logger.error(f"خطا در اجرای Flask: {e}")
    
    async def run_bot(self):
        """اجرای ربات تلگرام"""
        try:
            # بررسی توکن
            if not self.config.bot_token:
                logger.error("❌ توکن ربات تنظیم نشده است!")
                logger.error("لطفا یکی از روش‌های زیر را انجام دهید:")
                logger.error("1. متغیر محیطی TELEGRAM_BOT_TOKEN را تنظیم کنید")
                logger.error("2. فایل config.json را ایجاد و توکن را در آن قرار دهید")
                logger.error("3. فایل config_sample.json را کپی و توکن را در آن قرار دهید")
                return
            
            # ایجاد برنامه تلگرام
            logger.info("در حال راه‌اندازی ربات تلگرام...")
            self.application = Application.builder().token(self.config.bot_token).build()
            
            # تنظیم هندلرها
            self.setup_handlers()
            
            # تنظیم Webhook (برای Render)
            webhook_url = os.environ.get('RENDER_EXTERNAL_URL')
            if webhook_url:
                # حذف Webhook قبلی و تنظیم Webhook جدید
                await self.application.bot.delete_webhook()
                await self.application.bot.set_webhook(
                    url=f"{webhook_url}/telegram",
                    drop_pending_updates=True
                )
                logger.info(f"Webhook تنظیم شد: {webhook_url}/telegram")
            
            # راه‌اندازی ربات
            logger.info("✅ ربات تلگرام آماده است!")
            logger.info(f"🤖 نام ربات: {(await self.application.bot.get_me()).first_name}")
            logger.info("📝 منتظر پیام‌ها...")
            
            # اجرای ربات
            await self.application.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
        except Exception as e:
            logger.error(f"خطای بحرانی در اجرای ربات: {e}")
            raise
    
    def run(self):
        """اجرای همزمان Flask و Telegram Bot"""
        # اجرای Flask در thread جداگانه
        port = int(os.environ.get('PORT', 8080))
        flask_thread = threading.Thread(
            target=self.run_flask,
            args=(port,),
            daemon=True
        )
        flask_thread.start()
        
        # اجرای ربات تلگرام در thread اصلی
        asyncio.run(self.run_bot())

# تابع اصلی
def main():
    """تابع اصلی اجرای برنامه"""
    print("=" * 50)
    print("🤖 ربات تلگرام فوروارد پیام")
    print(f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 پایتون: 3.13")
    print("=" * 50)
    
    # ایجاد و اجرای ربات
    bot = TelegramForwardBot()
    bot.run()

if __name__ == "__main__":
    main()
