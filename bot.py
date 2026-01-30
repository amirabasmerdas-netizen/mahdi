import logging
import json
import os
import asyncio
from datetime import datetime
from typing import Dict
from flask import Flask, request, jsonify

from telegram import Update, Message, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

from config import Config

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class ForwarderBot:
    def __init__(self, token: str):
        self.token = token
        self.target_channel = Config.TARGET_CHANNEL
        self.data_file = Config.DATA_FILE
        self.admin_ids = Config.ADMIN_IDS
        self.subscribed_groups: Dict[str, Dict] = {}
        self.application = None
        
        self.load_data()
    
    def load_data(self):
        """بارگیری گروه‌های ذخیره شده از فایل"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.subscribed_groups = json.load(f)
                logger.info(f"Loaded {len(self.subscribed_groups)} groups from storage")
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            self.subscribed_groups = {}
    
    def save_data(self):
        """ذخیره گروه‌ها در فایل"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.subscribed_groups, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def add_group(self, group_id: str, group_title: str, added_by: int):
        """اضافه کردن گروه جدید"""
        self.subscribed_groups[group_id] = {
            'title': group_title,
            'added_by': added_by,
            'added_date': datetime.now().isoformat(),
            'active': True
        }
        self.save_data()
    
    def remove_group(self, group_id: str):
        """حذف گروه"""
        if group_id in self.subscribed_groups:
            del self.subscribed_groups[group_id]
            self.save_data()
            return True
        return False
    
    async def forward_message(self, bot: Bot, message: Message):
        """فروارد پیام به کانال"""
        try:
            group_id = str(message.chat.id)
            if group_id not in self.subscribed_groups:
                return
            
            group_info = self.subscribed_groups[group_id]
            if not group_info.get('active', True):
                return
            
            if message.service:
                return
            
            group_title = group_info.get('title', 'Unknown Group')
            
            if message.text:
                await bot.send_message(
                    chat_id=self.target_channel,
                    text=f"{message.text}\n\n📥 از گروه: {group_title}",
                    parse_mode=ParseMode.MARKDOWN if message.parse_mode == ParseMode.MARKDOWN else None
                )
            
            elif message.photo:
                caption = message.caption or ""
                if caption:
                    caption += f"\n\n📥 از گروه: {group_title}"
                else:
                    caption = f"📥 از گروه: {group_title}"
                
                await bot.send_photo(
                    chat_id=self.target_channel,
                    photo=message.photo[-1].file_id,
                    caption=caption
                )
            
            elif message.video:
                caption = message.caption or f"📥 از گروه: {group_title}"
                await bot.send_video(
                    chat_id=self.target_channel,
                    video=message.video.file_id,
                    caption=caption
                )
            
            elif message.document:
                caption = message.caption or f"📥 از گروه: {group_title}"
                await bot.send_document(
                    chat_id=self.target_channel,
                    document=message.document.file_id,
                    caption=caption
                )
            
            elif message.audio:
                caption = message.caption or f"📥 از گروه: {group_title}"
                await bot.send_audio(
                    chat_id=self.target_channel,
                    audio=message.audio.file_id,
                    caption=caption
                )
            
            elif message.voice:
                await bot.send_voice(
                    chat_id=self.target_channel,
                    voice=message.voice.file_id,
                    caption=f"📥 از گروه: {group_title}"
                )
            
            logger.info(f"Forwarded message from group {group_title}")
            
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        user = update.effective_user
        await update.message.reply_text(
            f"👋 سلام {user.first_name}!\n\n"
            "🤖 من ربات فروارد خودکار از گروه به کانال هستم.\n\n"
            "🔧 دستورات ادمین:\n"
            "/addgroup - اضافه کردن گروه فعلی\n"
            "/removegroup - حذف گروه فعلی\n"
            "/listgroups - لیست گروه‌های فعال\n"
            "/stats - آمار ربات\n\n"
            "📌 ابتدا مرا به گروه و کانال خود اضافه کنید."
        )
    
    async def add_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور اضافه کردن گروه"""
        user_id = update.effective_user.id
        chat = update.effective_chat
        
        if user_id not in self.admin_ids:
            await update.message.reply_text("⛔️ شما دسترسی لازم برای این کار را ندارید.")
            return
        
        if chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("⚠️ این دستور فقط در گروه‌ها قابل استفاده است.")
            return
        
        group_id = str(chat.id)
        group_title = chat.title or "بدون نام"
        
        if group_id in self.subscribed_groups:
            await update.message.reply_text(f"✅ گروه '{group_title}' قبلاً اضافه شده است.")
            return
        
        self.add_group(group_id, group_title, user_id)
        await update.message.reply_text(f"✅ گروه '{group_title}' با موفقیت اضافه شد.")
        
        logger.info(f"Group {group_title} added by user {user_id}")
    
    async def remove_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور حذف گروه"""
        user_id = update.effective_user.id
        chat = update.effective_chat
        
        if user_id not in self.admin_ids:
            await update.message.reply_text("⛔️ شما دسترسی لازم برای این کار را ندارید.")
            return
        
        group_id = str(chat.id)
        group_title = chat.title or "بدون نام"
        
        if self.remove_group(group_id):
            await update.message.reply_text(f"✅ گروه '{group_title}' حذف شد.")
            logger.info(f"Group {group_title} removed by user {user_id}")
        else:
            await update.message.reply_text("⚠️ این گروه در لیست فروارد وجود ندارد.")
    
    async def list_groups_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لیست گروه‌های فعال"""
        user_id = update.effective_user.id
        
        if user_id not in self.admin_ids:
            await update.message.reply_text("⛔️ شما دسترسی لازم برای این کار را ندارید.")
            return
        
        if not self.subscribed_groups:
            await update.message.reply_text("📭 هیچ گروهی اضافه نشده است.")
            return
        
        message = "📋 لیست گروه‌های فعال:\n\n"
        for idx, (group_id, group_info) in enumerate(self.subscribed_groups.items(), 1):
            status = "✅ فعال" if group_info.get('active', True) else "⭕ غیرفعال"
            message += f"{idx}. {group_info['title']}\n"
            message += f"   آیدی: {group_id}\n"
            message += f"   وضعیت: {status}\n\n"
        
        await update.message.reply_text(message)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """آمار ربات"""
        user_id = update.effective_user.id
        
        if user_id not in self.admin_ids:
            await update.message.reply_text("⛔️ شما دسترسی لازم برای این کار را ندارید.")
            return
        
        stats_message = (
            f"📊 آمار ربات:\n\n"
            f"👥 گروه‌های فعال: {len(self.subscribed_groups)}\n"
            f"👨‍💻 ادمین‌ها: {len(self.admin_ids)}\n"
            f"🎯 کانال مقصد: {self.target_channel or 'تنظیم نشده'}\n"
            f"🔄 وضعیت: {'✅ آنلاین' if self.target_channel else '⚠️ نیاز به تنظیم'}"
        )
        
        await update.message.reply_text(stats_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور راهنما"""
        help_text = (
            "📚 راهنمای ربات:\n\n"
            "1. ربات را به گروه مورد نظر اضافه کنید\n"
            "2. ربات را به کانال مقصد اضافه کنید (به عنوان ادمین)\n"
            "3. در گروه از دستور /addgroup استفاده کنید\n"
            "4. از این پس پیام‌های گروه به کانال فروارد می‌شوند\n\n"
            "🔧 دستورات:\n"
            "/start - شروع کار با ربات\n"
            "/addgroup - اضافه کردن گروه فعلی\n"
            "/removegroup - حذف گروه فعلی\n"
            "/listgroups - مشاهده لیست گروه‌ها\n"
            "/stats - مشاهده آمار\n"
            "/help - نمایش این راهنما"
        )
        await update.message.reply_text(help_text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش پیام‌های دریافتی"""
        try:
            message = update.message
            if not message:
                return
            
            await self.forward_message(context.bot, message)
            
        except Exception as e:
            logger.error(f"Error in handle_message: {e}")

# ایجاد نمونه ربات
bot_instance = ForwarderBot(Config.BOT_TOKEN)

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'service': 'Telegram Forwarder Bot',
        'groups': len(bot_instance.subscribed_groups)
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """دریافت آپدیت‌های تلگرام"""
    try:
        update = Update.de_json(request.get_json(force=True), bot_instance.application.bot)
        bot_instance.application.update_queue.put_nowait(update)
        return 'ok'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'error', 500

async def setup_application():
    """تنظیم اپلیکیشن تلگرام"""
    application = Application.builder().token(Config.BOT_TOKEN).build()
    bot_instance.application = application
    
    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", bot_instance.start_command))
    application.add_handler(CommandHandler("addgroup", bot_instance.add_group_command))
    application.add_handler(CommandHandler("removegroup", bot_instance.remove_group_command))
    application.add_handler(CommandHandler("listgroups", bot_instance.list_groups_command))
    application.add_handler(CommandHandler("stats", bot_instance.stats_command))
    application.add_handler(CommandHandler("help", bot_instance.help_command))
    
    # هندلر پیام‌ها
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        bot_instance.handle_message
    ))
    
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.DOCUMENT | filters.AUDIO | filters.VOICE,
        bot_instance.handle_message
    ))
    
    return application

async def main():
    """تابع اصلی راه‌اندازی"""
    application = await setup_application()
    
    # تنظیم وب‌هوک اگر آدرس مشخص شده
    if Config.WEBHOOK_URL:
        webhook_url = f"{Config.WEBHOOK_URL}/webhook"
        await application.bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook set to: {webhook_url}")
    else:
        logger.warning("⚠️ WEBHOOK_URL not set, using polling")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
    
    return application

# راه‌اندازی اپلیکیشن
def initialize_app():
    """راه‌اندازی اولیه"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        app.application = loop.run_until_complete(main())
        logger.info("✅ Bot application initialized successfully")
    except Exception as e:
        logger.error(f"❌ Initialization error: {e}")

# اجرای برنامه
if __name__ == '__main__':
    initialize_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
