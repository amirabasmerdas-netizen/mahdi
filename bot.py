#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات فوروارد گروه به کانال - نسخه 21.7
"""

import os
import json
import logging
import sys
from datetime import datetime

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),  # ارسال به stdout برای Render
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# تلاش برای وارد کردن کتابخانه‌ها
try:
    print("📦 در حال وارد کردن کتابخانه‌های تلگرام...")
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        filters,
        ContextTypes
    )
    print("✅ کتابخانه‌های تلگرام با موفقیت وارد شدند")
except ImportError as e:
    print(f"❌ خطا در وارد کردن کتابخانه‌ها: {e}")
    print("📌 لطفا مطمئن شوید requirements.txt شامل 'python-telegram-bot==21.7' است")
    sys.exit(1)

# متغیرهای جهانی برای تنظیمات
SOURCE_GROUP = None
DEST_CHANNEL = None

# بارگذاری تنظیمات
def load_settings():
    global SOURCE_GROUP, DEST_CHANNEL
    try:
        if os.path.exists('settings.json'):
            with open('settings.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                SOURCE_GROUP = data.get('source_group')
                DEST_CHANNEL = data.get('dest_channel')
                logger.info(f"تنظیمات بارگذاری شد: گروه={SOURCE_GROUP}, کانال={DEST_CHANNEL}")
    except Exception as e:
        logger.error(f"خطا در بارگذاری تنظیمات: {e}")

# ذخیره تنظیمات
def save_settings():
    try:
        with open('settings.json', 'w', encoding='utf-8') as f:
            json.dump({
                'source_group': SOURCE_GROUP,
                'dest_channel': DEST_CHANNEL,
                'last_updated': datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        logger.info("تنظیمات ذخیره شد")
    except Exception as e:
        logger.error(f"خطا در ذخیره تنظیمات: {e}")

# دستورات ربات
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    chat = update.effective_chat
    
    if chat.type in ['group', 'supergroup']:
        text = f"""
🤖 **ربات فوروارد گروه به کانال**

📍 **گروه فعلی:** {chat.title or 'بدون نام'}
🆔 **شناسه:** `{chat.id}`

🔧 **دستورات:**
/set - تنظیم این گروه به عنوان مبدا
/channel @کانال - تنظیم کانال مقصد
/test - تست فوروارد
/status - وضعیت ربات

⚠️ **نکته:** ربات باید در کانال ادمین باشد!
        """
    else:
        text = """
🤖 **ربات فوروارد گروه به کانال**

📌 **نحوه استفاده:**
1. ربات را به گروه اضافه کنید
2. در گروه `/set` را بفرستید
3. سپس `/channel @کانال_شما` را بفرستید
4. ربات باید در کانال ادمین باشد

🔧 **دستورات:**
/set - تنظیم گروه
/channel - تنظیم کانال  
/test - تست
/status - وضعیت
        """
    
    await update.message.reply_text(text)
    logger.info(f"Start از {chat.id}")

async def set_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /set"""
    global SOURCE_GROUP
    
    chat = update.effective_chat
    
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ این دستور فقط در گروه‌ها قابل استفاده است!")
        return
    
    SOURCE_GROUP = str(chat.id)
    save_settings()
    
    text = f"""
✅ **گروه مبدا تنظیم شد!**

🏷️ نام: {chat.title or 'بدون نام'}
🆔 شناسه: `{chat.id}`

حالا کانال مقصد را تنظیم کنید:
`/channel @کانال_شما`
    """
    
    await update.message.reply_text(text)
    logger.info(f"گروه تنظیم شد: {chat.id}")

async def channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /channel"""
    global DEST_CHANNEL
    
    if not context.args:
        await update.message.reply_text("❌ شناسه کانال را وارد کنید\nمثال: `/channel @my_channel`")
        return
    
    channel = context.args[0].strip()
    
    # اعتبارسنجی شناسه کانال
    if not (channel.startswith('@') or channel.startswith('-100')):
        await update.message.reply_text(
            "❌ شناسه کانال نامعتبر!\n"
            "✅ باید با @ شروع شود (مثل @channel)\n"
            "✅ یا با -100 شروع شود (شناسه عددی)"
        )
        return
    
    DEST_CHANNEL = channel
    save_settings()
    
    text = f"""
✅ **کانال مقصد تنظیم شد!**

🆔 شناسه: `{channel}`

⚠️ **توجه مهم:** 
ربات باید در این کانال **ادمین** باشد!
در غیر این صورت نمی‌تواند پیام فوروارد کند.

برای تست: `/test`
    """
    
    await update.message.reply_text(text)
    logger.info(f"کانال تنظیم شد: {channel}")

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /test"""
    if not SOURCE_GROUP or not DEST_CHANNEL:
        await update.message.reply_text(
            "❌ ابتدا گروه و کانال را تنظیم کنید!\n\n"
            f"گروه: {'✅ تنظیم شده' if SOURCE_GROUP else '❌ تنظیم نشده'}\n"
            f"کانال: {'✅ تنظیم شده' if DEST_CHANNEL else '❌ تنظیم نشده'}\n\n"
            "دستورات:\n"
            "/set - تنظیم گروه\n"
            "/channel @کانال - تنظیم کانال"
        )
        return
    
    try:
        await update.message.reply_text("🔄 در حال تست فوروارد...")
        
        # ایجاد پیام تست
        test_msg = await update.message.reply_text(f"""
🧪 **تست فوروارد ربات**
⏰ {datetime.now().strftime('%H:%M:%S')}
📅 {datetime.now().strftime('%Y-%m-%d')}

📍 مبدا: {SOURCE_GROUP}
🎯 مقصد: {DEST_CHANNEL}

✅ اگر این پیام را می‌بینید، تست موفق بود!
        """)
        
        # فوروارد پیام تست به کانال
        await test_msg.forward(chat_id=DEST_CHANNEL)
        
        await update.message.reply_text("✅ تست موفقیت‌آمیز بود!")
        logger.info(f"تست فوروارد انجام شد از {SOURCE_GROUP} به {DEST_CHANNEL}")
        
    except Exception as e:
        error_msg = str(e)
        await update.message.reply_text(f"❌ خطا در تست:\n{error_msg[:150]}")
        logger.error(f"خطا در تست فوروارد: {e}")
        
        # تشخیص نوع خطا
        if "Forbidden" in error_msg:
            await update.message.reply_text("⚠️ احتمالاً ربات در کانال ادمین نیست!")
        elif "Chat not found" in error_msg:
            await update.message.reply_text("⚠️ کانال یافت نشد! شناسه کانال را بررسی کنید.")
        elif "Not enough rights" in error_msg:
            await update.message.reply_text("⚠️ ربات در کانال دسترسی کافی ندارد!")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /status"""
    text = f"""
📊 **وضعیت ربات**

📍 **گروه مبدا:**
{SOURCE_GROUP or '❌ تنظیم نشده'}

🎯 **کانال مقصد:**
{DEST_CHANNEL or '❌ تنظیم نشده'}

💡 **وضعیت فوروارد:** {'✅ آماده' if SOURCE_GROUP and DEST_CHANNEL else '⚠️ نیاز به تنظیم'}

🔧 **دستورات:**
/set - تنظیم گروه
/channel - تنظیم کانال  
/test - تست
    """
    
    await update.message.reply_text(text)

# تابع اصلی فوروارد پیام‌ها
async def forward_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فوروارد تمام پیام‌های گروه به کانال"""
    
    # لاگ پیام دریافتی
    chat = update.effective_chat
    chat_id = str(chat.id)
    
    logger.info(f"📨 پیام دریافت شد از چت: {chat_id}")
    
    # بررسی تنظیمات
    if not SOURCE_GROUP or not DEST_CHANNEL:
        logger.info("⚠️ تنظیمات کامل نیست - فوروارد نمی‌شود")
        return
    
    # بررسی اینکه پیام از گروه مبدا است
    if chat_id != SOURCE_GROUP:
        logger.info(f"⏭️ پیام از گروه مبدا نیست (منتظر: {SOURCE_GROUP})")
        return
    
    logger.info(f"✅ پیام از گروه مبدا است. در حال فوروارد به {DEST_CHANNEL}")
    
    try:
        # فوروارد پیام
        await update.message.forward(chat_id=DEST_CHANNEL)
        logger.info("✅ پیام با موفقیت فوروارد شد")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ خطا در فوروارد: {error_msg}")
        
        # لاگ جزئیات بیشتر
        try:
            if update.message.text:
                logger.info(f"متن پیام: {update.message.text[:100]}")
            elif update.message.caption:
                logger.info(f"کپشن: {update.message.caption[:100]}")
        except:
            pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت خطاها"""
    logger.error(f"خطا در پردازش: {context.error}")

async def main():
    """تابع اصلی async"""
    
    print("=" * 60)
    print("🤖 ربات فوروارد گروه به کانال")
    print("🚀 نسخه 21.7 - سازگار با Python 3.13")
    print(f"🐍 پایتون: {sys.version.split()[0]}")
    print("=" * 60)
    
    # بارگذاری تنظیمات
    load_settings()
    
    # گرفتن توکن
    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        print("❌ خطا: TELEGRAM_BOT_TOKEN یافت نشد!")
        print("لطفا در Render متغیر محیطی TELEGRAM_BOT_TOKEN را تنظیم کنید")
        return
    
    print(f"✅ توکن: {TOKEN[:15]}...")
    print(f"📍 گروه مبدا: {SOURCE_GROUP or 'تنظیم نشده'}")
    print(f"🎯 کانال مقصد: {DEST_CHANNEL or 'تنظیم نشده'}")
    print("🔄 در حال راه‌اندازی ربات...")
    
    try:
        # ایجاد Application
        app = Application.builder().token(TOKEN).build()
        
        # افزودن دستورات
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("set", set_command))
        app.add_handler(CommandHandler("channel", channel_command))
        app.add_handler(CommandHandler("test", test_command))
        app.add_handler(CommandHandler("status", status_command))
        
        # افزودن هندلر برای فوروارد پیام‌ها
        app.add_handler(MessageHandler(
            filters.ALL & ~filters.COMMAND,
            forward_messages
        ))
        
        # مدیریت خطا
        app.add_error_handler(error_handler)
        
        # گرفتن اطلاعات ربات
        bot = await app.bot.get_me()
        print(f"✅ ربات: @{bot.username}")
        print(f"🤖 نام: {bot.first_name}")
        print("📡 شروع به گوش دادن برای پیام‌ها...")
        print("=" * 60)
        
        # شروع polling
        await app.run_polling(
            drop_pending_updates=True,
            allowed_updates=None  # همه بروزرسانی‌ها
        )
        
    except Exception as e:
        print(f"❌ خطای بحرانی: {e}")
        logger.error(f"خطای بحرانی: {e}", exc_info=True)

if __name__ == "__main__":
    import asyncio
    
    # اجرای main با asyncio.run
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 ربات متوقف شد")
    except Exception as e:
        print(f"❌ خطا: {e}")
