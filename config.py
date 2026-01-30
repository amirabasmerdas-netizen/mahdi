import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # توکن ربات از @BotFather
    BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    
    # آیدی عددی کانال مقصد (مثلاً: -1001234567890)
    TARGET_CHANNEL = os.getenv('TARGET_CHANNEL', '')
    
    # پورت برای وب‌سرور (اختیاری)
    PORT = int(os.getenv('PORT', 5000))
    
    # آدرس وب‌هوک (برای deploy روی سرور)
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    
    # فایل ذخیره‌سازی گروه‌ها
    DATA_FILE = 'subscribed_groups.json'
    
    # دسترسی ادمین‌ها (آیدی عددی)
    ADMIN_IDS = []
    
    # مقداردهی ADMIN_IDS
    admin_ids_str = os.getenv('ADMIN_IDS', '')
    if admin_ids_str:
        ADMIN_IDS = list(map(int, admin_ids_str.split(',')))
