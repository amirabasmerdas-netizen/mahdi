#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات فوروارد گروه به کانال - نسخه تضمینی
"""

import os
import json
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# کلاس برای ذخیره تنظیمات
class Config:
    def __init__(self):
        self.source_group = None
        self.dest_channel = None
        self.load()
    
    def load(self):
        """بارگذاری تنظیمات از فایل"""
        try:
            if os.path.exists('settings.json'):
                with open('settings.json', 'r') as f:
                    data = json.load(f)
                    self.source_group = data.get('source_group')
                    self.dest_channel = data.get('dest_channel')
        except:
            pass
    
    def save(self):
        """ذخیره تنظیمات در فایل"""
        try:
            with open('settings.json', 'w') as f:
                json.dump({
                    'source_group': self.source_group,
                    'dest_channel': self.dest_channel
                }, f)
        except:
            pass
    
    def is_ready(self):
        """بررسی کامل بودن تنظیمات"""
        return self.source_group and self.dest_channel

config = Config()

# دستورات ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    chat = update.effective_chat
    
    if chat.type in ['group', 'supergroup']:
        text = f"""
🤖 **ربات فوروارد فعال است!**

📍 **گروه فعلی:** {chat.title or 'بدون نام'}
🆔 **شناسه:** `{chat.id}`

برای تنظیم این گروه به عنوان مبدا:
`/set`

برای تنظیم کانال مقصد:
`/channel @کانال_شما`

برای تست:
`/test`
        """
    else:
        text = """
🤖 **ربات فوروارد گروه به کانال**

📌 **نحوه استفاده:**
1. ربات را به گروه اضافه کنید
2. در گروه `/set` را بفرستید
3. سپس `/channel @کانال_شما` را بفرستید
4. ربات باید در کانال ادمین باشد

🧪 تست: `/test`
📊 وضعیت: `/status`
        """
    
    await update.message.reply_text(text)
    logger.info(f"Start از {chat.id}")

async def set_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /set - تنظیم گروه مبدا"""
    chat = update.effective_chat
    
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ این دستور فقط در گروه‌ها کار می‌کند!")
        return
    
    config.source_group = str(chat.id)
    config.save()
    
    text = f"""
✅ **گروه مبدا تنظیم شد!**

🏷️ نام: {chat.title or 'بدون نام'}
🆔 شناسه: `{chat.id}`

حالا کانال را تنظیم کنید:
`/channel @کانال_شما`
    """
    
    await update.message.reply_text(text)
    logger.info(f"گروه تنظیم شد: {chat.id}")

async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /channel - تنظیم کانال مقصد"""
    if not context.args:
        await update.message.reply_text("❌ شناسه کانال را وارد کنید\nمثال: `/channel @my_channel`")
        return
    
    channel = context.args[0].strip()
    
    if not (channel.startswith('@') or channel.startswith('-100')):
        await update.message.reply_text("❌ شناسه نامعتبر!\nبا @ یا -100 شروع شود")
        return
    
    config.dest_channel = channel
    config.save()
    
    text = f"""
✅ **کانال مقصد تنظیم شد!**

🆔 شناسه: `{channel}`

⚠️ ربات باید در این کانال ادمین باشد!

برای تست: `/test`
    """
    
    await update.message.reply_text(text)
    logger.info(f"کانال تنظیم شد: {channel}")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /test - تست فوروارد"""
    if not config.is_ready():
        await update.message.reply_text("❌ ابتدا گروه و کانال را تنظیم کنید!")
        return
    
    try:
        await update.message.reply_text("🔄 در حال تست فوروارد...")
        
        # پیام تست
        test_msg = await update.message.reply_text(f"""
🧪 **تست فوروارد ربات**
⏰ {datetime.now().strftime('%H:%M:%S')}
✅ ربات فعال است!
        """)
        
        # فوروارد پیام
        await test_msg.forward(chat_id=config.dest_channel)
        
        await update.message.reply_text("✅ تست موفق بود!")
        logger.info("تست موفقیت‌آمیز")
        
    except Exception as e:
        error = str(e)
        await update.message.reply_text(f"❌ خطا: {error[:100]}")
        logger.error(f"خطا در تست: {e}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /status - وضعیت"""
    text = f"""
📊 **وضعیت ربات**

📍 **گروه مبدا:**
{config.source_group or '❌ تنظیم نشده'}

🎯 **کانال مقصد:**
{config.dest_channel or '❌ تنظیم نشده'}

💡 **وضعیت:** {'✅ آماده' if config.is_ready() else '⚠️ نیاز به تنظیم'}
    """
    
    await update.message.reply_text(text)

# مهم: تابع فوروارد پیام‌ها
async def forward_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فوروارد تمام پیام‌های گروه به کانال"""
    
    # لاگ برای دیباگ
    chat_id = str(update.effective_chat.id)
    logger.info(f"📨 پیام دریافتی از چت: {chat_id}")
    
    # بررسی تنظیمات
    if not config.is_ready():
        logger.info("⚠️ تنظیمات کامل نیست")
        return
    
    # بررسی اینکه پیام از گروه مبدا است
    if chat_id != config.source_group:
        logger.info(f"⏭️ پیام از گروه مبدا نیست (منتظر: {config.source_group})")
        return
    
    logger.info(f"✅ پیام از گروه مبدا است. در حال فوروارد به {config.dest_channel}")
    
    try:
        # فوروارد پیام
        await update.message.forward(chat_id=config.dest_channel)
        logger.info("✅ پیام با موفقیت فوروارد شد")
        
    except Exception as e:
        logger.error(f"❌ خطا در فوروارد: {e}")
        
        # اگر خطای دسترسی بود، اطلاع بده
        if "Forbidden" in str(e):
            try:
                await update.message.reply_text("⚠️ خطا: ربات در کانال ادمین نیست یا دسترسی ندارد")
            except:
                pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت خطاها"""
    logger.error(f"خطا: {context.error}")

async def main():
    """تابع اصلی"""
    # گرفتن توکن از متغیر محیطی
    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        logger.error("❌ توکن ربات یافت نشد!")
        print("لطفا TELEGRAM_BOT_TOKEN را در Render تنظیم کنید")
        return
    
    print("=" * 50)
    print("🤖 ربات فوروارد گروه به کانال")
    print("🚀 در حال راه‌اندازی...")
    print("=" * 50)
    
    # ساخت اپلیکیشن
    app = Application.builder().token(TOKEN).build()
    
    # افزودن دستورات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set", set_group))
    app.add_handler(CommandHandler("channel", set_channel))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("status", status))
    
    # افزودن هندلر برای فوروارد تمام پیام‌ها
    app.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND,
        forward_all_messages
    ))
    
    # مدیریت خطا
    app.add_error_handler(error_handler)
    
    # گرفتن اطلاعات ربات
    bot = await app.bot.get_me()
    print(f"✅ ربات: @{bot.username}")
    print(f"🤖 نام: {bot.first_name}")
    
    # نمایش تنظیمات فعلی
    print(f"📍 گروه مبدا: {config.source_group or 'تنظیم نشده'}")
    print(f"🎯 کانال مقصد: {config.dest_channel or 'تنظیم نشده'}")
    print("📡 در حال گوش دادن برای پیام‌ها...")
    print("=" * 50)
    
    # اجرای ربات
    await app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
