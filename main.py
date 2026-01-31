import os
import logging
from typing import Dict, Tuple
from dataclasses import dataclass, asdict
import json
from datetime import datetime

from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from flask import Flask, request, jsonify

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ساختار داده‌ای برای تنظیمات
@dataclass
class BotConfig:
    source_chat_id: str = ""
    destination_chat_id: str = ""
    bot_token: str = ""
    webhook_url: str = ""
    admin_id: str = ""

class ForwardBot:
    def __init__(self):
        self.config = BotConfig()
        self.app = None
        self.flask_app = Flask(__name__)
        self.setup_flask_routes()
        
    def setup_flask_routes(self):
        """تنظیم مسیرهای Flask"""
        @self.flask_app.route('/')
        def home():
            return "ربات فوروارد پیام در حال اجراست!"
        
        @self.flask_app.route('/set_source/<chat_id>')
        def set_source(chat_id):
            """تنظیم گروه مبدا از طریق وب"""
            self.config.source_chat_id = chat_id
            self.save_config()
            return f"گروه مبدا تنظیم شد: {chat_id}"
        
        @self.flask_app.route('/set_destination/<chat_id>')
        def set_destination(chat_id):
            """تنظیم گروه مقصد از طریق وب"""
            self.config.destination_chat_id = chat_id
            self.save_config()
            return f"گروه مقصد تنظیم شد: {chat_id}"
        
        @self.flask_app.route('/status')
        def status():
            """نمایش وضعیت فعلی"""
            return jsonify(asdict(self.config))
    
    def load_config(self):
        """بارگذاری تنظیمات از فایل"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config = BotConfig(**data)
                    logger.info("تنظیمات از فایل بارگذاری شد")
        except Exception as e:
            logger.error(f"خطا در بارگذاری تنظیمات: {e}")
    
    def save_config(self):
        """ذخیره تنظیمات در فایل"""
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(asdict(self.config), f, indent=4, ensure_ascii=False)
            logger.info("تنظیمات ذخیره شد")
        except Exception as e:
            logger.error(f"خطا در ذخیره تنظیمات: {e}")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        user = update.effective_user
        welcome_message = (
            f"سلام {user.first_name} 👋\n"
            "به ربات فوروارد پیام خوش آمدید!\n\n"
            "دستورات موجود:\n"
            "/set_source - تنظیم گروه مبدا\n"
            "/set_destination - تنظیم گروه مقصد\n"
            "/show_config - نمایش تنظیمات فعلی\n"
            "/help - راهنمایی\n\n"
            "برای تنظیم گروه مبدا، ابتدا ربات را به گروه اضافه کرده و سپس از دستور /set_source استفاده کنید."
        )
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /help"""
        help_text = (
            "📋 راهنمای ربات فوروارد پیام:\n\n"
            "1. ابتدا ربات را به گروه مبدا و مقصد اضافه کنید\n"
            "2. از دستور /set_source برای تنظیم گروه مبدا استفاده کنید\n"
            "3. از دستور /set_destination برای تنظیم گروه مقصد استفاده کنید\n"
            "4. ربات به صورت خودکار پیام‌ها را فوروارد می‌کند\n\n"
            "نکات مهم:\n"
            "• ربات باید در هر دو گروه عضو باشد\n"
            "• برای تنظیم گروه، دستور را در همان گروه ارسال کنید\n"
            "• از دستور /show_config برای مشاهده تنظیمات استفاده کنید"
        )
        await update.message.reply_text(help_text)
    
    async def set_source_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تنظیم گروه مبدا"""
        chat_id = str(update.effective_chat.id)
        self.config.source_chat_id = chat_id
        self.save_config()
        
        await update.message.reply_text(
            f"✅ گروه مبدا با موفقیت تنظیم شد!\n"
            f"شناسه گروه: {chat_id}\n\n"
            "از این پس پیام‌های این گروه به گروه مقصد فوروارد می‌شوند."
        )
        logger.info(f"گروه مبدا تنظیم شد: {chat_id}")
    
    async def set_destination_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تنظیم گروه مقصد"""
        chat_id = str(update.effective_chat.id)
        self.config.destination_chat_id = chat_id
        self.save_config()
        
        await update.message.reply_text(
            f"✅ گروه مقصد با موفقیت تنظیم شد!\n"
            f"شناسه گروه: {chat_id}\n\n"
            "پیام‌های گروه مبدا به این گروه فوروارد خواهند شد."
        )
        logger.info(f"گروه مقصد تنظیم شد: {chat_id}")
    
    async def show_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش تنظیمات فعلی"""
        config_text = (
            "⚙️ تنظیمات فعلی ربات:\n\n"
            f"گروه مبدا: {self.config.source_chat_id or 'تنظیم نشده'}\n"
            f"گروه مقصد: {self.config.destination_chat_id or 'تنظیم نشده'}\n\n"
            "برای تغییر تنظیمات از دستورات زیر استفاده کنید:\n"
            "/set_source - تنظیم گروه مبدا\n"
            "/set_destination - تنظیم گروه مقصد"
        )
        await update.message.reply_text(config_text)
    
    async def forward_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """فوروارد پیام از گروه مبدا به مقصد"""
        # بررسی اینکه پیام از گروه مبدا است
        current_chat_id = str(update.effective_chat.id)
        
        if not self.config.source_chat_id or not self.config.destination_chat_id:
            return
        
        if current_chat_id != self.config.source_chat_id:
            return
        
        try:
            # فوروارد پیام به گروه مقصد
            await update.message.forward(
                chat_id=self.config.destination_chat_id
            )
            logger.info(f"پیام فوروارد شد از {current_chat_id} به {self.config.destination_chat_id}")
            
        except Exception as e:
            logger.error(f"خطا در فوروارد پیام: {e}")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت خطاها"""
        logger.error(f"خطا در پردازش بروزرسانی: {context.error}")
    
    def setup_handlers(self, application: Application):
        """تنظیم هندلرهای ربات"""
        # دستورات
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("set_source", self.set_source_chat))
        application.add_handler(CommandHandler("set_destination", self.set_destination_chat))
        application.add_handler(CommandHandler("show_config", self.show_config))
        
        # هندلر پیام‌ها
        application.add_handler(
            MessageHandler(
                filters.ALL & ~filters.COMMAND,
                self.forward_message
            )
        )
        
        # هندلر خطا
        application.add_error_handler(self.error_handler)
    
    async def setup_webhook(self, application: Application, webhook_url: str):
        """تنظیم وب‌هوک"""
        await application.bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True
        )
        logger.info(f"وب‌هوک تنظیم شد: {webhook_url}")
    
    def run_flask(self, port: int = 8080):
        """اجرای سرور Flask"""
        self.flask_app.run(host='0.0.0.0', port=port)
    
    async def run_bot(self):
        """اجرای ربات تلگرام"""
        # بارگذاری تنظیمات
        self.load_config()
        
        if not self.config.bot_token:
            logger.error("توکن ربات تنظیم نشده است!")
            return
        
        # ایجاد برنامه تلگرام
        self.app = Application.builder().token(self.config.bot_token).build()
        
        # تنظیم هندلرها
        self.setup_handlers(self.app)
        
        # تنظیم وب‌هوک
        if self.config.webhook_url:
            await self.setup_webhook(self.app, self.config.webhook_url)
        
        logger.info("ربات در حال اجراست...")
        
        # شروع ربات
        await self.app.run_polling(allowed_updates=Update.ALL_TYPES)

# تابع اصلی برای اجرا در Render
def create_app():
    """ایجاد برنامه برای Render"""
    bot = ForwardBot()
    
    # اگر توکن ربات در متغیرهای محیطی وجود دارد
    token = os.environ.get('TELEGRAM_BOT_TOKEN',"8574884910:AAGNF8jpjM-SXEsrEb1rsHW6obxbWEs90sQ")
    webhook_url = os.environ.get('WEBHOOK_URL')
    
    if token:
        bot.config.bot_token = token
    if webhook_url:
        bot.config.webhook_url = webhook_url
    
    return bot.flask_app

# برای اجرای محلی
async def main():
    """تابع اصلی برای اجرای محلی"""
    bot = ForwardBot()
    
    # بارگذاری تنظیمات
    bot.load_config()
    
    # اگر توکن وجود ندارد، از کاربر بگیر
    if not bot.config.bot_token:
        bot.config.bot_token = input("لطفا توکن ربات تلگرام را وارد کنید: ")
        bot.save_config()
    
    if not bot.config.webhook_url:
        bot.config.webhook_url = input("لطفا آدرس وب‌هوک را وارد کنید (اختیاری): ")
        bot.save_config()
    
    # اجرای ربات
    await bot.run_bot()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

