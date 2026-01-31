#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات فوروارد پیام از گروه به کانال - نسخه دیباگ
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any

from telegram import Update, Chat
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# تنظیمات لاگ‌گیری دقیق
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,  # تغییر به DEBUG برای جزئیات بیشتر
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_debug.log', encoding='utf-8')
    ]
)
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
            'admin_id': '',
            'last_updated': '',
            'group_name': '',
            'channel_name': ''
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    default_config.update(saved_config)
        except Exception as e:
            logger.error(f"خطا در بارگذاری تنظیمات: {e}")
        
        logger.info(f"تنظیمات بارگذاری شد: {default_config}")
        return default_config
    
    def save_config(self):
        """ذخیره تنظیمات"""
        try:
            self.config['last_updated'] = datetime.now().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info(f"تنظیمات ذخیره شد: {self.config}")
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
            'errors': 0,
            'start_time': datetime.now(),
            'last_message_time': None
        }
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        try:
            user = update.effective_user
            chat = update.effective_chat
            
            logger.info(f"📩 START از {user.id} در چت {chat.id} (نوع: {chat.type})")
            
            if chat.type in ['group', 'supergroup']:
                welcome_text = f"""
🤖 **ربات فوروارد گروه به کانال**

🏷️ **گروه فعلی:** {chat.title or 'بدون نام'}
🆔 **شناسه گروه:** `{chat.id}`

🔧 **برای تنظیم این گروه به عنوان مبدا:**
`/setgroup`

📤 **برای تنظیم کانال مقصد:**
`/setchannel @کانال_شما`

📊 **وضعیت فعلی:** `/status`
                """
            else:
                welcome_text = """
🤖 **ربات فوروارد گروه به کانال**

📍 **لطفا مرا به گروه مورد نظر اضافه کنید.**

📝 **پس از اضافه کردن به گروه:**
1. در گروه دستور `/setgroup` را ارسال کنید
2. سپس کانال را با `/setchannel @کانال_شما` تنظیم کنید
3. مطمئن شوید ربات در کانال ادمین است

❓ **راهنما:** `/help`
                """
            
            await update.message.reply_text(welcome_text)
            logger.info("✅ پاسخ start ارسال شد")
            
        except Exception as e:
            logger.error(f"❌ خطا در start: {e}", exc_info=True)
    
    async def set_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /setgroup"""
        try:
            chat = update.effective_chat
            
            # بررسی نوع چت
            if chat.type not in ['group', 'supergroup']:
                await update.message.reply_text("❌ این دستور فقط در گروه‌ها قابل استفاده است!")
                return
            
            chat_id = str(chat.id)
            chat_title = chat.title or "بدون نام"
            
            logger.info(f"📝 تنظیم گروه: {chat_title} ({chat_id})")
            
            # ذخیره تنظیمات
            self.config.set('source_group_id', chat_id)
            self.config.set('group_name', chat_title)
            
            response = f"""
✅ **گروه مبدا تنظیم شد!**

🏷️ **نام:** {chat_title}
🆔 **شناسه:** `{chat_id}`
📋 **نوع:** {chat.type}
👥 **اعضا:** {chat.get_member_count() if hasattr(chat, 'get_member_count') else 'نامشخص'}

➡️ **گام بعدی:** کانال مقصد را تنظیم کنید:
`/setchannel @کانال_شما`

⚠️ **توجه:** ربات باید در کانال ادمین باشد!
            """
            
            await update.message.reply_text(response)
            logger.info(f"✅ گروه تنظیم شد: {chat_title} ({chat_id})")
            
            # لاگ تنظیمات فعلی
            logger.info(f"⚙️ تنظیمات فعلی: {self.config.config}")
            
        except Exception as e:
            logger.error(f"❌ خطا در setgroup: {e}", exc_info=True)
            await update.message.reply_text(f"❌ خطا: {str(e)}")
    
    async def set_channel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /setchannel"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "❌ لطفا شناسه کانال را وارد کنید:\n"
                    "📝 مثال: `/setchannel @my_channel`\n"
                    "🔢 یا: `/setchannel -1001234567890`"
                )
                return
            
            channel_id = context.args[0].strip()
            logger.info(f"📝 تنظیم کانال: {channel_id}")
            
            # اعتبارسنجی شناسه
            if not (channel_id.startswith('@') or channel_id.startswith('-100')):
                await update.message.reply_text(
                    "❌ شناسه کانال نامعتبر!\n\n"
                    "✅ فرمت صحیح:\n"
                    "• با @ شروع شود: `@channel_name`\n"
                    "• با -100 شروع شود: `-1001234567890`\n\n"
                    "📌 **نکته:** برای گرفتن شناسه کانال:\n"
                    "1. یک پست از کانال فوروارد کنید به @username_to_id_bot\n"
                    "2. شناسه عددی را کپی کنید"
                )
                return
            
            # ذخیره تنظیمات
            self.config.set('destination_channel_id', channel_id)
            
            # تست دسترسی به کانال
            try:
                chat_info = await context.bot.get_chat(channel_id)
                channel_name = chat_info.title or "بدون نام"
                self.config.set('channel_name', channel_name)
                logger.info(f"✅ اطلاعات کانال دریافت شد: {channel_name}")
            except Exception as e:
                logger.warning(f"⚠️ نتوانستم اطلاعات کانال را بگیرم: {e}")
                channel_name = "نامشخص"
            
            response = f"""
✅ **کانال مقصد تنظیم شد!**

🏷️ **نام:** {channel_name}
🆔 **شناسه:** `{channel_id}`

🔧 **تنظیمات فعلی:**
• گروه مبدا: {'✅ تنظیم شده' if self.config.get('source_group_id') else '❌ تنظیم نشده'}
• کانال مقصد: ✅ تنظیم شده
• توکن ربات: {'✅ تنظیم شده' if self.config.get('bot_token') else '❌ تنظیم نشده'}

📤 **آماده فوروارد:** {'✅ بله' if self.config.is_configured() else '❌ خیر'}

⚠️ **تأیید نهایی:**
1. ربات باید در کانال ادمین باشد
2. برای تست از `/test` استفاده کنید
            """
            
            await update.message.reply_text(response)
            logger.info(f"✅ کانال تنظیم شد: {channel_id}")
            
        except Exception as e:
            logger.error(f"❌ خطا در setchannel: {e}", exc_info=True)
            await update.message.reply_text(f"❌ خطا: {str(e)}")
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /test - تست کامل"""
        try:
            chat = update.effective_chat
            
            logger.info(f"🧪 تست از چت {chat.id} ({chat.type})")
            
            if not self.config.is_configured():
                await update.message.reply_text(
                    "❌ تنظیمات کامل نیست!\n\n"
                    "📋 **تنظیمات مورد نیاز:**\n"
                    f"• گروه مبدا: {'✅' if self.config.get('source_group_id') else '❌'}\n"
                    f"• کانال مقصد: {'✅' if self.config.get('destination_channel_id') else '❌'}\n"
                    f"• توکن ربات: {'✅' if self.config.get('bot_token') else '❌'}\n\n"
                    "🔧 **راه‌حل:**\n"
                    "1. در گروه: `/setgroup`\n"
                    "2. سپس: `/setchannel @کانال_شما`"
                )
                return
            
            # اطلاعات فعلی
            source_group = self.config.get('source_group_id')
            dest_channel = self.config.get('destination_channel_id')
            
            await update.message.reply_text("🔄 در حال تست...")
            
            # تست 1: بررسی گروه مبدا
            try:
                group_info = await context.bot.get_chat(source_group)
                test1 = f"✅ گروه مبدا:\n• نام: {group_info.title}\n• شناسه: {source_group}"
                logger.info(f"✅ گروه مبدا تأیید شد: {group_info.title}")
            except Exception as e:
                test1 = f"❌ خطا در دسترسی به گروه:\n{str(e)[:100]}"
                logger.error(f"❌ خطا در دسترسی به گروه: {e}")
            
            # تست 2: بررسی کانال مقصد
            try:
                channel_info = await context.bot.get_chat(dest_channel)
                test2 = f"✅ کانال مقصد:\n• نام: {channel_info.title}\n• شناسه: {dest_channel}"
                logger.info(f"✅ کانال مقصد تأیید شد: {channel_info.title}")
            except Exception as e:
                test2 = f"❌ خطا در دسترسی به کانال:\n{str(e)[:100]}"
                logger.error(f"❌ خطا در دسترسی به کانال: {e}")
            
            # تست 3: فوروارد پیام تست
            test3 = ""
            try:
                test_message = f"""
🧪 **تست فوروارد ربات**
⏰ {datetime.now().strftime('%H:%M:%S')}
📅 {datetime.now().strftime('%Y-%m-%d')}

📍 **مبدا:** {group_info.title if 'group_info' in locals() else source_group}
🎯 **مقصد:** {channel_info.title if 'channel_info' in locals() else dest_channel}

✅ این پیام تست فوروارد است.
                """
                
                # ارسال پیام تست
                sent_msg = await update.message.reply_text(test_message)
                
                # فوروارد پیام به کانال
                await sent_msg.forward(chat_id=dest_channel)
                
                test3 = "✅ فوروارد موفقیت‌آمیز!"
                logger.info("✅ تست فوروارد موفق")
                
            except Exception as e:
                test3 = f"❌ خطا در فوروارد:\n{str(e)[:150]}"
                logger.error(f"❌ خطا در فوروارد: {e}", exc_info=True)
            
            # نمایش نتایج
            result = f"""
📊 **نتایج تست:**

1. {test1}

2. {test2}

3. {test3}

{'🎉 **آماده به کار!**' if '✅' in test3 else '⚠️ **نیاز به بررسی**'}
            """
            
            await update.message.reply_text(result)
            
        except Exception as e:
            logger.error(f"❌ خطا در تست: {e}", exc_info=True)
            await update.message.reply_text(f"❌ خطا در تست: {str(e)[:200]}")
    
    async def debug_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /debug - اطلاعات دیباگ"""
        try:
            chat = update.effective_chat
            message = update.message
            
            debug_info = f"""
🔍 **اطلاعات دیباگ**

💬 **پیام فعلی:**
• چت ID: `{chat.id}`
• نوع چت: {chat.type}
• عنوان: {chat.title or 'ندارد'}
• کاربر: {message.from_user.id if message else 'ندارد'}

⚙️ **تنظیمات ربات:**
• گروه مبدا: `{self.config.get('source_group_id')}`
• کانال مقصد: `{self.config.get('destination_channel_id')}`
• تطابق گروه: {'✅ بله' if str(chat.id) == self.config.get('source_group_id') else '❌ خیر'}

📊 **آمار:**
• پیام‌های فوروارد شده: {self.stats['messages_forwarded']}
• آخرین پیام: {self.stats['last_message_time'] or 'هیچ'}

🔄 **وضعیت:**
• تنظیمات کامل: {'✅ بله' if self.config.is_configured() else '❌ خیر'}
• ربات فعال: {'✅ بله' if self.application else '❌ خیر'}
            """
            
            await update.message.reply_text(debug_info)
            logger.info(f"🔍 دیباگ برای چت {chat.id}")
            
        except Exception as e:
            logger.error(f"خطا در دیباگ: {e}")
    
    async def forward_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """فوروارد پیام‌ها از گروه به کانال"""
        try:
            message = update.message
            chat = update.effective_chat
            
            # لاگ تمام پیام‌های دریافتی
            logger.info(f"📨 پیام دریافت شده:")
            logger.info(f"  چت ID: {chat.id}")
            logger.info(f"  نوع چت: {chat.type}")
            logger.info(f"  عنوان چت: {chat.title or 'ندارد'}")
            logger.info(f"  نوع پیام: {message.content_type if message else 'نامشخص'}")
            logger.info(f"  متن پیام: {message.text[:100] if message and message.text else 'بدون متن'}")
            
            # بررسی تنظیمات
            if not self.config.is_configured():
                logger.info("⚠️ تنظیمات کامل نیست، فوروارد نمی‌شود")
                return
            
            source_group_id = self.config.get('source_group_id')
            dest_channel_id = self.config.get('destination_channel_id')
            
            logger.info(f"🔍 بررسی تطابق:")
            logger.info(f"  گروه مبدا تنظیم شده: {source_group_id}")
            logger.info(f"  چت فعلی: {chat.id}")
            logger.info(f"  تطابق: {'✅ بله' if str(chat.id) == source_group_id else '❌ خیر'}")
            
            # بررسی اینکه پیام از گروه مبدا است
            if str(chat.id) != source_group_id:
                logger.info(f"⏭️ پیام از گروه مبدا نیست، نادیده گرفته شد")
                return
            
            logger.info(f"✅ پیام از گروه مبدا است، در حال فوروارد...")
            
            # فوروارد پیام
            try:
                await message.forward(chat_id=dest_channel_id)
                
                # آپدیت آمار
                self.stats['messages_forwarded'] += 1
                self.stats['last_message_time'] = datetime.now().strftime('%H:%M:%S')
                
                logger.info(f"✅ پیام فوروارد شد به {dest_channel_id}")
                logger.info(f"📊 کل فورواردها: {self.stats['messages_forwarded']}")
                
                # لاگ هر 5 پیام
                if self.stats['messages_forwarded'] % 5 == 0:
                    logger.info(f"📈 آمار: {self.stats['messages_forwarded']} پیام فوروارد شده")
                
            except Exception as e:
                logger.error(f"❌ خطا در فوروارد پیام: {e}", exc_info=True)
                self.stats['errors'] += 1
                
                # تلاش برای ارسال خطا به ادمین
                try:
                    admin_id = self.config.get('admin_id')
                    if admin_id:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=f"⚠️ خطا در فوروارد:\n{str(e)[:200]}"
                        )
                except:
                    pass
        
        except Exception as e:
            logger.error(f"❌ خطای کلی در پردازش پیام: {e}", exc_info=True)
            self.stats['errors'] += 1
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /status"""
        try:
            status_emoji = "✅" if self.config.is_configured() else "⚠️"
            
            # زمان فعالیت
            uptime = datetime.now() - self.stats['start_time']
            hours, remainder = divmod(uptime.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            uptime_str = f"{int(hours)}h {int(minutes)}m"
            
            # اطلاعات گروه و کانال
            group_info = f"`{self.config.get('source_group_id')}`"
            if self.config.get('group_name'):
                group_info = f"{self.config.get('group_name')}\n`{self.config.get('source_group_id')}`"
            
            channel_info = f"`{self.config.get('destination_channel_id')}`"
            if self.config.get('channel_name'):
                channel_info = f"{self.config.get('channel_name')}\n`{self.config.get('destination_channel_id')}`"
            
            status_text = f"""
{status_emoji} **وضعیت ربات**

📊 **آمار عملکرد:**
• پیام‌های فوروارد شده: `{self.stats['messages_forwarded']}`
• خطاها: `{self.stats['errors']}`
• زمان فعالیت: `{uptime_str}`
• آخرین پیام: `{self.stats['last_message_time'] or 'هیچ'}`

📍 **گروه مبدا:**
{group_info or '❌ تنظیم نشده'}

🎯 **کانال مقصد:**
{channel_info or '❌ تنظیم نشده'}

🔧 **تنظیمات:**
• توکن ربات: {'✅' if self.config.get('bot_token') else '❌'}
• تطابق گروه: {'✅ بله' if self.config.is_configured() else '❌ خیر'}

💡 **وضعیت:** {'✅ آماده' if self.config.is_configured() else '⚠️ نیاز به تنظیم'}

🔍 **برای دیباگ:** `/debug`
🧪 **برای تست:** `/test`
            """
            
            await update.message.reply_text(status_text)
            
        except Exception as e:
            logger.error(f"خطا در status: {e}")
            await update.message.reply_text(f"❌ خطا: {str(e)}")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت خطاها"""
        logger.error(f"❌ خطا در پردازش: {context.error}", exc_info=True)
    
    def setup_handlers(self, application: Application):
        """تنظیم هندلرها"""
        # دستورات
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("setgroup", self.set_group_command))
        application.add_handler(CommandHandler("setchannel", self.set_channel_command))
        application.add_handler(CommandHandler("test", self.test_command))
        application.add_handler(CommandHandler("debug", self.debug_command))
        application.add_handler(CommandHandler("status", self.status_command))
        
        # فوروارد تمام پیام‌ها (به جز دستورات)
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
                logger.error("❌ توکن ربات یافت نشد!")
                logger.error("لطفا TELEGRAM_BOT_TOKEN را تنظیم کنید")
                return
            
            logger.info("🚀 شروع راه‌اندازی ربات...")
            
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
            logger.info(f"✅ ربات: @{bot.username} ({bot.first_name})")
            logger.info(f"🆔 ربات ID: {bot.id}")
            
            # نمایش تنظیمات
            logger.info(f"⚙️ تنظیمات:")
            logger.info(f"  گروه مبدا: {self.config.get('source_group_id')}")
            logger.info(f"  کانال مقصد: {self.config.get('destination_channel_id')}")
            logger.info(f"  تنظیمات کامل: {self.config.is_configured()}")
            
            if not self.config.is_configured():
                logger.warning("⚠️ تنظیمات کامل نیست! از دستورات /setgroup و /setchannel استفاده کنید")
            else:
                logger.info("✅ ربات آماده فوروارد است!")
            
            # شروع Polling
            logger.info("📡 شروع polling...")
            
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                timeout=20,
                poll_interval=0.5
            )
            
            logger.info("✅ ربات فعال و در حال گوش دادن...")
            
            # نگه داشتن برنامه
            stop_event = asyncio.Event()
            await stop_event.wait()
            
        except KeyboardInterrupt:
            logger.info("👋 توقف توسط کاربر")
        except Exception as e:
            logger.error(f"❌ خطای بحرانی: {e}", exc_info=True)
        finally:
            if self.application:
                logger.info("🛑 در حال توقف ربات...")
                try:
                    await self.application.stop()
                    await self.application.shutdown()
                except:
                    pass
            logger.info("🔚 ربات متوقف شد")

# تابع اصلی
def main():
    """تابع اصلی"""
    print("=" * 60)
    print("🤖 ربات فوروارد گروه به کانال - نسخه دیباگ")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # بررسی توکن
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ خطا: TELEGRAM_BOT_TOKEN یافت نشد!")
        print("در Render: Settings → Environment Variables")
        return
    
    print(f"✅ توکن: {token[:15]}...")
    print("🔧 سطح لاگ: DEBUG")
    print("📁 فایل لاگ: bot_debug.log")
    print("💡 از دستور /debug برای اطلاعات بیشتر استفاده کنید")
    print("=" * 60)
    
    # اجرای ربات
    bot = TelegramForwardBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n👋 توقف شد")
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    main()
