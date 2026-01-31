#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فایل اجرایی ساده برای Render
"""

import os
import sys

# افزودن مسیر فعلی به sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # وارد کردن و اجرای ربات
    from bot import main
    import asyncio
    
    print("🚀 شروع ربات فوروارد...")
    asyncio.run(main())
    
except ImportError as e:
    print(f"❌ خطا در وارد کردن ماژول‌ها: {e}")
    print("📌 لطفا مطمئن شوید فایل bot.py در همان پوشه است")
    sys.exit(1)
except Exception as e:
    print(f"❌ خطای عمومی: {e}")
    sys.exit(1)
