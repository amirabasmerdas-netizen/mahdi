#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات ساده تلگرام برای فوروارد پیام از گروه به کانال
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
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# کلاس مدیریت تنظیمات
class ConfigManager:
    def __init__(self):
        self.config_file = 'config.json'
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """بارگذاری تنظیمات از فایل یا ایجاد جدید"""
        default_config = {
            'source_group_id': '',
            'destination_channel_id': '',
            'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
            'admin_id': '',
            'last_updated': ''
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    # ادغام با تنظیمات پیش‌فرض
                    default_config.update(saved_config)
        except Exception as e:
            logger.error(f"خطا در بارگذاری تنظیمات: {e}")
        
        return default_config
    
    def save_config(self):
        """ذخیره تنظیمات در فایل"""
        try:
            self.config['last_updated'] = datetime.now().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info("تنظیمات ذخیره شد")
        except Exception as e:
            logger.error(f"خطا در ذخیره تنظیمات: {e}")
    
    def get(self, key: str, default=None):
        """گرفتن مقدار از تنظیمات"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """تنظیم مقدار"""
        self.config[key] = value
        self.save_config()
    
    def is_configured(self) -> bool:
        """بررسی کامل بودن تنظیمات"""
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
            'errors': 0,
            'start_time': datetime.now()
        }
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        try:
            logger.info(f"دریافت دستور start از کاربر: {update.effective_user.id}")
            
            welcome_text = """
🤖 **ربات فوروارد گروه به کانال**

🔧 **دستورات:**
/setgroup - تنظیم گروه فعلی به عنوان مبدا
/setchannel @channel_id - تنظیم کانال مقصد
/status - نمایش وضعیت
/test - تست فوروارد
/help - راهنما

📝 **نحوه استفاده:**
1. ربات را به گروه و کانال اضافه کنید
2. در گروه: /setgroup
3. کانال: /setchannel @channel_name
4. ربات در کانال باید ادمین باشد

🔄 ربات در حال اجراست و پیام‌ها را فوروارد می‌کند!
            """
            
            await update.message.reply_text(welcome_text)
            logger.info("پاسخ start ارسال شد")
            
        except Exception as e:
            logger.error(f"خطا در دستور start: {e}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /help"""
        help_text = """
📚 **راهنمای ربات**

🎯 **کاربرد:** فوروارد خودکار پیام از گروه به کانال

🔧 **دستورات اصلی:**
• /setgroup - تنظیم گروه مبدا
• /setchannel @channel - تنظیم کانال مقصد
• /status - وضعیت ربات
• /test - تست فوروارد
• /help - این راهنما

⚙️ **تنظیمات:**
- تمام پیام‌ها فوروارد می‌شوند
- پشتیبانی از متن، عکس، ویدیو، صوت، فایل
- ربات باید در کانال ادمین باشد

🌐 **سرور:** ربات روی Render اجرا می‌شود
            """
        await update.message.reply_text(help_text)
    
    async def set_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /setgroup"""
        try:
            # بررسی اینکه در گروه هستیم
            if update.effective_chat.type not in ['group', 'supergroup']:
                await update.message.reply_text("❌ این دستور فقط در گروه‌ها کار می‌کند!")
                return
            
            chat_id = str(update.effective_chat.id)
            chat_title = update.effective_chat.title or "بدون نام"
            
            self.config.set('source_group_id', chat_id)
            
            response = f"""
✅ **گروه مبدا تنظیم شد!**

🏷️ نام: {chat_title}
🆔 شناسه: `{chat_id}`
📅 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}

➡️ حالا کانال مقصد را با /setchannel تنظیم کنید.
            """
            
            await update.message.reply_text(response)
            logger.info(f"گروه تنظیم شد: {chat_id} ({chat_title})")
            
        except Exception as e:
            logger.error(f"خطا در setgroup: {e}")
            await update.message.reply_text(f"❌ خطا: {str(e)}")
    
    async def set_channel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /setchannel"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "❌ لطفا شناسه کانال را وارد کنید:\n"
                    "مثال: `/setchannel @my_channel`\n"
                    "یا: `/setchannel -1001234567890`"
                )
                return
            
            channel_id = context.args[0].strip()
            
            # اعتبارسنجی شناسه کانال
            if not (channel_id.startswith('@') or channel_id.startswith('-100')):
                await update.message.reply_text(
                    "❌ شناسه کانال نامعتبر!\n"
                    "✅ باید با @ شروع شود (مثل @channel)\n"
                    "✅ یا با -100 شروع شود (شناسه عددی)"
                )
                return
            
            self.config.set('destination_channel_id', channel_id)
            
            response = f"""
✅ **کانال مقصد تنظیم شد!**

🆔 شناسه: `{channel_id}`
📅 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}

⚠️ **توجه:** ربات باید در این کانال ادمین باشد!
            """
            
            await update.message.reply_text(response)
            logger.info(f"کانال تنظیم شد: {channel_id}")
            
        except Exception as e:
            logger.error(f"خطا در setchannel: {e}")
            await update.message.reply_text(f"❌ خطا: {str(e)}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /status"""
        try:
            status_emoji = "✅" if self.config.is_configured() else "⚠️"
            
            # محاسبه زمان فعالیت
            uptime = datetime.now() - self.stats['start_time']
            hours, remainder = divmod(uptime.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            
            status_text = f"""
{status_emoji} **وضعیت ربات**

📊 **آمار:**
• پیام‌های فوروارد شده: {self.stats['messages_forwarded']}
• خطاها: {self.stats['errors']}
• زمان فعالیت: {uptime_str}

📍 **گروه مبدا:**
{self.config.get('source_group_id', '❌ تنظیم نشده') or '❌ تنظیم نشده'}

🎯 **کانال مقصد:**
{self.config.get('destination_channel_id', '❌ تنظیم نشده') or '❌ تنظیم نشده'}

🔑 **توکن ربات:** {'✅ تنظیم شده' if self.config.get('bot_token') else '❌ تنظیم نشده'}

💡 **وضعیت:** {'✅ آماده' if self.config.is_configured() else '⚠️ نیاز به تنظیم'}

🔄 **سرور:** Render (آنلاین)
            """
            
            await update.message.reply_text(status_text)
            
        except Exception as e:
            logger.error(f"خطا در status: {e}")
            await update.message.reply_text(f"❌ خطا: {str(e)}")
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /test"""
        try:
            if not self.config.is_configured():
                await update.message.reply_text("❌ ابتدا گروه و کانال را تنظیم کنید!")
                return
            
            await update.message.reply_text("🔄 در حال تست فوروارد...")
            
            # ایجاد یک پیام تست
            test_text = f"""
🧪 **تست فوروارد ربات**
⏰ زمان: {datetime.now().strftime('%H:%M:%S')}
📅 تاریخ: {datetime.now().strftime('%Y-%m-%d')}
✅ اگر این پیام را می‌بینید، ربات کار می‌کند!
            """
            
            # ارسال پیام تست
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=test_text
            )
            
            # فوروارد پیام تست به کانال
            test_msg = await update.message.reply_text("📤 در حال فوروارد به کانال...")
            await test_msg.forward(chat_id=self.config.get('destination_channel_id'))
            
            await update.message.reply_text("✅ تست موفقیت‌آمیز بود!")
            logger.info("تست فوروارد انجام شد")
            
        except Exception as e:
            error_msg = f"❌ خطا در تست: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(error_msg)
            self.stats['errors'] += 1
    
    async def forward_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """فوروارد تمام پیام‌ها"""
        try:
            # بررسی تنظیمات
            if not self.config.is_configured():
                return
            
            # بررسی اینکه پیام از گروه مبدا است
            current_chat_id = str(update.effective_chat.id)
            source_group_id = self.config.get('source_group_id')
            
            if current_chat_id != source_group_id:
                return
            
            # فوروارد پیام
            await update.message.forward(
                chat_id=self.config.get('destination_channel_id')
            )
            
            # آپدیت آمار
            self.stats['messages_forwarded'] += 1
            
            # لاگ هر 10 پیام
            if self.stats['messages_forwarded'] % 10 == 0:
                logger.info(f"پیام فوروارد شده: {self.stats['messages_forwarded']}")
            
        except Exception as e:
            logger.error(f"خطا در فوروارد: {e}")
            self.stats['errors'] += 1
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت خطاها"""
        logger.error(f"خطا: {context.error}")
        
        # ارسال پیام خطا به ادمین
        try:
            admin_id = self.config.get('admin_id')
            if admin_id:
                error_msg = f"⚠️ خطا در ربات:\n{str(context.error)[:200]}"
                await context.bot.send_message(chat_id=admin_id, text=error_msg)
        except:
            pass
    
    def setup_handlers(self, application: Application):
        """تنظیم هندلرها"""
        # دستورات
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("setgroup", self.set_group_command))
        application.add_handler(CommandHandler("setchannel", self.set_channel_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("test", self.test_command))
        
        # فوروارد پیام‌ها
        application.add_handler(
            MessageHandler(
                filters.ALL & ~filters.COMMAND,
                self.forward_all_messages
            )
        )
        
        # مدیریت خطا
        application.add_error_handler(self.error_handler)
    
    async def run(self):
        """اجرای ربات"""
        try:
            # بررسی توکن
            bot_token = self.config.get('bot_token')
            if not bot_token:
                logger.error("❌ توکن ربات تنظیم نشده!")
                logger.error("لطفا متغیر محیطی TELEGRAM_BOT_TOKEN را تنظیم کنید")
                return
            
            logger.info("🚀 در حال راه‌اندازی ربات...")
            
            # ایجاد Application
            self.application = (
                Application.builder()
                .token(bot_token)
                .build()
            )
            
            # تنظیم هندلرها
            self.setup_handlers(self.application)
            
            # دریافت اطلاعات ربات
            bot = await self.application.bot.get_me()
            logger.info(f"✅ ربات راه‌اندازی شد: @{bot.username}")
            logger.info(f"🤖 نام ربات: {bot.first_name}")
            
            # بررسی تنظیمات
            if self.config.is_configured():
                logger.info("✅ تنظیمات کامل است")
                logger.info(f"📤 گروه مبدا: {self.config.get('source_group_id')}")
                logger.info(f"📥 کانال مقصد: {self.config.get('destination_channel_id')}")
            else:
                logger.warning("⚠️ تنظیمات کامل نیست")
                logger.info("از دستورات /setgroup و /setchannel استفاده کنید")
            
            # شروع Polling
            logger.info("📡 شروع به گوش دادن برای پیام‌ها...")
            
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
            # نگه داشتن برنامه فعال
            logger.info("✅ ربات آماده است و در حال اجرا...")
            
            # ایجاد یک event برای نگه داشتن برنامه
            stop_event = asyncio.Event()
            
            # ثبت handler برای سیگنال‌های خاتمه
            def signal_handler():
                logger.info("دریافت سیگنال خاتمه...")
                stop_event.set()
            
            # اجرا تا دریافت سیگنال توقف
            await stop_event.wait()
            
        except KeyboardInterrupt:
            logger.info("ربات متوقف شد (KeyboardInterrupt)")
        except Exception as e:
            logger.error(f"خطای بحرانی: {e}", exc_info=True)
        finally:
            # توقف ربات
            if self.application:
                logger.info("در حال توقف ربات...")
                try:
                    await self.application.stop()
                    await self.application.shutdown()
                except:
                    pass
            logger.info("ربات متوقف شد")

# تابع اصلی
def main():
    """تابع اصلی"""
    print("=" * 50)
    print("🤖 ربات تلگرام فوروارد گروه به کانال")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🌐 اجرا روی Render")
    print("=" * 50)
    
    # بررسی توکن
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ خطا: توکن ربات یافت نشد!")
        print("لطفا متغیر محیطی TELEGRAM_BOT_TOKEN را تنظیم کنید")
        print("در Render: Settings → Environment Variables")
        return
    
    print(f"✅ توکن یافت شد: {token[:10]}...")
    
    # ایجاد و اجرای ربات
    bot = TelegramForwardBot()
    
    try:
        # اجرای ربات
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n👋 ربات متوقف شد")
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
