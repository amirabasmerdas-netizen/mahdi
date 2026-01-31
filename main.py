#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات ساده فوروارد - حداقل وابستگی
"""

import os
import logging
import asyncio
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# تنظیمات ساده
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ذخیره تنظیمات در متغیرهای ساده
SOURCE_GROUP = None
DEST_CHANNEL = None
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    await update.message.reply_text("🤖 ربات فوروارد فعال است!")
    logger.info(f"Start از {update.effective_chat.id}")

async def setgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /setgroup"""
    global SOURCE_GROUP
    chat = update.effective_chat
    
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ فقط در گروه!")
        return
    
    SOURCE_GROUP = str(chat.id)
    await update.message.reply_text(f"✅ گروه تنظیم شد: {SOURCE_GROUP}")
    logger.info(f"گروه تنظیم شد: {SOURCE_GROUP}")

async def setchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /setchannel"""
    global DEST_CHANNEL
    
    if not context.args:
        await update.message.reply_text("❌ شناسه کانال را وارد کنید")
        return
    
    DEST_CHANNEL = context.args[0].strip()
    await update.message.reply_text(f"✅ کانال تنظیم شد: {DEST_CHANNEL}")
    logger.info(f"کانال تنظیم شد: {DEST_CHANNEL}")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /test"""
    if not SOURCE_GROUP or not DEST_CHANNEL:
        await update.message.reply_text("❌ ابتدا گروه و کانال را تنظیم کنید")
        return
    
    await update.message.reply_text("🔄 تست...")
    test_msg = await update.message.reply_text("پیام تست")
    await test_msg.forward(chat_id=DEST_CHANNEL)
    await update.message.reply_text("✅ تست موفق!")
    logger.info("تست انجام شد")

async def forward_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فوروارد همه پیام‌ها"""
    global SOURCE_GROUP, DEST_CHANNEL
    
    if not SOURCE_GROUP or not DEST_CHANNEL:
        return
    
    chat_id = str(update.effective_chat.id)
    
    if chat_id != SOURCE_GROUP:
        return
    
    try:
        await update.message.forward(chat_id=DEST_CHANNEL)
        logger.info(f"پیام فوروارد شد از {chat_id} به {DEST_CHANNEL}")
    except Exception as e:
        logger.error(f"خطا در فوروارد: {e}")

async def main():
    """تابع اصلی"""
    if not BOT_TOKEN:
        logger.error("❌ توکن یافت نشد!")
        return
    
    print("🤖 ربات فوروارد - در حال راه‌اندازی...")
    
    # ساخت Application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # افزودن هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setgroup", setgroup))
    app.add_handler(CommandHandler("setchannel", setchannel))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_all))
    
    # اطلاعات ربات
    bot = await app.bot.get_me()
    print(f"✅ ربات: @{bot.username}")
    print("📡 در حال گوش دادن...")
    
    # اجرای ربات
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات ساده فوروارد - حداقل وابستگی
"""

import os
import logging
import asyncio
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# تنظیمات ساده
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ذخیره تنظیمات در متغیرهای ساده
SOURCE_GROUP = None
DEST_CHANNEL = None
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    await update.message.reply_text("🤖 ربات فوروارد فعال است!")
    logger.info(f"Start از {update.effective_chat.id}")

async def setgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /setgroup"""
    global SOURCE_GROUP
    chat = update.effective_chat
    
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ فقط در گروه!")
        return
    
    SOURCE_GROUP = str(chat.id)
    await update.message.reply_text(f"✅ گروه تنظیم شد: {SOURCE_GROUP}")
    logger.info(f"گروه تنظیم شد: {SOURCE_GROUP}")

async def setchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /setchannel"""
    global DEST_CHANNEL
    
    if not context.args:
        await update.message.reply_text("❌ شناسه کانال را وارد کنید")
        return
    
    DEST_CHANNEL = context.args[0].strip()
    await update.message.reply_text(f"✅ کانال تنظیم شد: {DEST_CHANNEL}")
    logger.info(f"کانال تنظیم شد: {DEST_CHANNEL}")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /test"""
    if not SOURCE_GROUP or not DEST_CHANNEL:
        await update.message.reply_text("❌ ابتدا گروه و کانال را تنظیم کنید")
        return
    
    await update.message.reply_text("🔄 تست...")
    test_msg = await update.message.reply_text("پیام تست")
    await test_msg.forward(chat_id=DEST_CHANNEL)
    await update.message.reply_text("✅ تست موفق!")
    logger.info("تست انجام شد")

async def forward_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فوروارد همه پیام‌ها"""
    global SOURCE_GROUP, DEST_CHANNEL
    
    if not SOURCE_GROUP or not DEST_CHANNEL:
        return
    
    chat_id = str(update.effective_chat.id)
    
    if chat_id != SOURCE_GROUP:
        return
    
    try:
        await update.message.forward(chat_id=DEST_CHANNEL)
        logger.info(f"پیام فوروارد شد از {chat_id} به {DEST_CHANNEL}")
    except Exception as e:
        logger.error(f"خطا در فوروارد: {e}")

async def main():
    """تابع اصلی"""
    if not BOT_TOKEN:
        logger.error("❌ توکن یافت نشد!")
        return
    
    print("🤖 ربات فوروارد - در حال راه‌اندازی...")
    
    # ساخت Application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # افزودن هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setgroup", setgroup))
    app.add_handler(CommandHandler("setchannel", setchannel))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_all))
    
    # اطلاعات ربات
    bot = await app.bot.get_me()
    print(f"✅ ربات: @{bot.username}")
    print("📡 در حال گوش دادن...")
    
    # اجرای ربات
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات فوروارد پیام از گروه به کانال - نسخه 21.7
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# تنظیمات لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
# غیرفعال کردن لاگ‌های اضافی
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# کلاس مدیریت تنظیمات
class ConfigManager:
    def __init__(self):
        self.config_file = 'config.json'
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """بارگذاری تنظیمات"""
        default_config = {
            'source_group_id': '',
            'destination_channel_id': '',
            'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
            'last_updated': ''
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    default_config.update(saved_config)
        except Exception as e:
            logger.error(f"خطا در بارگذاری تنظیمات: {e}")
        
        logger.info(f"تنظیمات بارگذاری شد")
        return default_config
    
    def save_config(self):
        """ذخیره تنظیمات"""
        try:
            self.config['last_updated'] = datetime.now().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info("تنظیمات ذخیره شد")
        except Exception as e:
            logger.error(f"خطا در ذخیره تنظیمات: {e}")
    
    def get(self, key: str, default=None):
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save_config()
    
    def is_configured(self) -> bool:
        return all([
            self.config.get('source_group_id'),
            self.config.get('destination_channel_id'),
            self.config.get('bot_token')
        ])

# کلاس اصلی ربات
class TelegramForwardBot:
    def __init__(self):
        self.config = ConfigManager()
        self.application = None
        self.stats = {
            'messages_forwarded': 0,
            'start_time': datetime.now()
        }
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        try:
            chat = update.effective_chat
            
            if chat.type in ['group', 'supergroup']:
                welcome_text = f"""
🤖 **ربات فوروارد گروه به کانال**

📍 **گروه فعلی:** {chat.title or 'بدون نام'}
🆔 **شناسه:** `{chat.id}`

برای تنظیم این گروه به عنوان مبدا:
`/setgroup`

برای تنظیم کانال مقصد:
`/setchannel @کانال_شما`

برای تست:
`/test`
                """
            else:
                welcome_text = """
🤖 **ربات فوروارد گروه به کانال**

📌 **نحوه استفاده:**
1. ربات را به گروه اضافه کنید
2. در گروه دستور `/setgroup` را ارسال کنید
3. سپس کانال را با `/setchannel @کانال_شما` تنظیم کنید
4. ربات باید در کانال ادمین باشد

🧪 **تست:** `/test`
📊 **وضعیت:** `/status`
                """
            
            await update.message.reply_text(welcome_text)
            logger.info(f"پاسخ start به {chat.id}")
            
        except Exception as e:
            logger.error(f"خطا در start: {e}")
    
    async def set_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /setgroup"""
        try:
            chat = update.effective_chat
            
            if chat.type not in ['group', 'supergroup']:
                await update.message.reply_text("❌ فقط در گروه‌ها قابل استفاده است!")
                return
            
            chat_id = str(chat.id)
            chat_title = chat.title or "بدون نام"
            
            self.config.set('source_group_id', chat_id)
            
            response = f"""
✅ **گروه مبدا تنظیم شد!**

🏷️ نام: {chat_title}
🆔 شناسه: `{chat_id}`

حالا کانال مقصد را تنظیم کنید:
`/setchannel @کانال_شما`
            """
            
            await update.message.reply_text(response)
            logger.info(f"گروه تنظیم شد: {chat_title} ({chat_id})")
            
        except Exception as e:
            logger.error(f"خطا در setgroup: {e}")
            await update.message.reply_text(f"❌ خطا: {str(e)}")
    
    async def set_channel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /setchannel"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "❌ شناسه کانال را وارد کنید:\n"
                    "مثال: `/setchannel @my_channel`"
                )
                return
            
            channel_id = context.args[0].strip()
            
            if not (channel_id.startswith('@') or channel_id.startswith('-100')):
                await update.message.reply_text(
                    "❌ شناسه نامعتبر!\n"
                    "✅ باید با @ شروع شود (مثل @channel)\n"
                    "✅ یا با -100 شروع شود"
                )
                return
            
            self.config.set('destination_channel_id', channel_id)
            
            response = f"""
✅ **کانال مقصد تنظیم شد!**

🆔 شناسه: `{channel_id}`

⚠️ **توجه:** ربات باید در کانال ادمین باشد!

برای تست از `/test` استفاده کنید.
            """
            
            await update.message.reply_text(response)
            logger.info(f"کانال تنظیم شد: {channel_id}")
            
        except Exception as e:
            logger.error(f"خطا در setchannel: {e}")
            await update.message.reply_text(f"❌ خطا: {str(e)}")
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /test"""
        try:
            if not self.config.is_configured():
                await update.message.reply_text(
                    "❌ تنظیمات کامل نیست!\n"
                    f"گروه: {'✅' if self.config.get('source_group_id') else '❌'}\n"
                    f"کانال: {'✅' if self.config.get('destination_channel_id') else '❌'}\n\n"
                    "از /setgroup و /setchannel استفاده کنید."
                )
                return
            
            await update.message.reply_text("🔄 در حال تست...")
            
            # ایجاد پیام تست
            test_text = f"""
🧪 **تست فوروارد**
⏰ {datetime.now().strftime('%H:%M:%S')}
✅ ربات فعال است!
            """
            
            sent_msg = await update.message.reply_text(test_text)
            
            # فوروارد به کانال
            await sent_msg.forward(chat_id=self.config.get('destination_channel_id'))
            
            await update.message.reply_text("✅ تست موفقیت‌آمیز بود!")
            logger.info("تست فوروارد انجام شد")
            
        except Exception as e:
            error_msg = f"❌ خطا در تست: {str(e)[:100]}"
            await update.message.reply_text(error_msg)
            logger.error(f"خطا در تست: {e}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /status"""
        try:
            status_emoji = "✅" if self.config.is_configured() else "⚠️"
            
            uptime = datetime.now() - self.stats['start_time']
            hours, remainder = divmod(uptime.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            uptime_str = f"{int(hours)}h {int(minutes)}m"
            
            status_text = f"""
{status_emoji} **وضعیت ربات**

📊 **آمار:**
• پیام‌های فوروارد شده: {self.stats['messages_forwarded']}
• زمان فعالیت: {uptime_str}

📍 **گروه مبدا:**
{self.config.get('source_group_id') or '❌ تنظیم نشده'}

🎯 **کانال مقصد:**
{self.config.get('destination_channel_id') or '❌ تنظیم نشده'}

💡 **وضعیت:** {'✅ آماده' if self.config.is_configured() else '⚠️ نیاز به تنظیم'}
            """
            
            await update.message.reply_text(status_text)
            
        except Exception as e:
            logger.error(f"خطا در status: {e}")
    
    async def forward_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """فوروارد پیام‌ها"""
        try:
            # بررسی تنظیمات
            if not self.config.is_configured():
                return
            
            chat = update.effective_chat
            source_group_id = self.config.get('source_group_id')
            
            # بررسی اینکه پیام از گروه مبدا است
            if str(chat.id) != source_group_id:
                return
            
            logger.info(f"پیام از گروه مبدا دریافت شد: {chat.id}")
            
            # فوروارد پیام
            await update.message.forward(
                chat_id=self.config.get('destination_channel_id')
            )
            
            # آپدیت آمار
            self.stats['messages_forwarded'] += 1
            
            logger.info(f"پیام فوروارد شد (کل: {self.stats['messages_forwarded']})")
            
        except Exception as e:
            logger.error(f"خطا در فوروارد: {e}")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت خطاها"""
        logger.error(f"خطا: {context.error}")
    
    def setup_handlers(self, application: Application):
        """تنظیم هندلرها"""
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("setgroup", self.set_group_command))
        application.add_handler(CommandHandler("setchannel", self.set_channel_command))
        application.add_handler(CommandHandler("test", self.test_command))
        application.add_handler(CommandHandler("status", self.status_command))
        
        application.add_handler(
            MessageHandler(
                filters.ALL & ~filters.COMMAND,
                self.forward_messages
            )
        )
        
        application.add_error_handler(self.error_handler)
    
    async def run_bot(self):
        """اجرای ربات"""
        try:
            # بررسی توکن
            bot_token = self.config.get('bot_token')
            if not bot_token:
                logger.error("❌ توکن یافت نشد!")
                return
            
            logger.info("🚀 راه‌اندازی ربات...")
            
            # ایجاد Application
            self.application = Application.builder().token(bot_token).build()
            
            # تنظیم هندلرها
            self.setup_handlers(self.application)
            
            # اطلاعات ربات
            bot = await self.application.bot.get_me()
            logger.info(f"✅ ربات: @{bot.username}")
            logger.info(f"⚙️ تنظیمات کامل: {self.config.is_configured()}")
            
            # شروع ربات
            logger.info("📡 شروع به کار...")
            
            # استفاده از run_polling به جای start_polling
            await self.application.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
        except Exception as e:
            logger.error(f"❌ خطا: {e}")
            raise
    
    def run(self):
        """اجرای اصلی"""
        print("=" * 50)
        print("🤖 ربات فوروارد گروه به کانال")
        print("=" * 50)
        
        asyncio.run(self.run_bot())

if __name__ == "__main__":
    bot = TelegramForwardBot()
    bot.run()

