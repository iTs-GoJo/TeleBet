# TeleBet — Telegram Betting Bot

Welcome to TeleBet — a lively, lightweight Telegram bot for a fun economy/game experience. TeleBet lets users earn and spend points, buy/sell gold, trade simulated cryptocurrencies, collect and trade NFTs, use bank/loans, open lootboxes, and compete on leaderboards.

This README is provided in English and Persian (فارسی).

---

English — Quick Overview
=========================

What TeleBet offers
- Playable economy: Points (score), Gold, Crypto (simulated), NFTs, Stars, Bank & Loans.
- Game features: betting, lootboxes, gifts, leaderboards.
- Admin tools: add NFTs/crypto/gifts and broadcast messages.
- Simple file-based storage (JSON) for easy local hosting.

Requirements
- Python 3.10+
- python-telegram-bot (v20+ recommended)

Install
```bash
pip install python-telegram-bot
```

Setup (2 minutes)
1. Create a bot via BotFather and get your token.
2. Set environment variables (recommended):
   - Linux / macOS:
     ```bash
     export BOT_TOKEN="<your-bot-token>"
     export ADMIN_ID="<your-telegram-id>"   # optional
     ```
   - Windows (PowerShell):
     ```powershell
     $env:BOT_TOKEN = "<your-bot-token>"
     $env:ADMIN_ID = "<your-telegram-id>"
     ```
3. Run:
```bash
python main.py
```

Core user commands
- /start — Register & welcome message
- /help — Show commands
- /bet <amount> <زوج|فرد> — Place an even/odd bet
- /gold price | buy <amt> | sell <amt> — Gold market (price in points)
- /crypto list | buy <name> <amt> | sell <name> <amt> | price <name> | portfolio
- /nft list | buy <name> | sell <name> [price] | portfolio
- /bank de <amt> | wi <amt> | ln <amt> | pr — deposit / withdraw / loan / repay
- /stars buy <amt> | sell <amt>
- /box — open a lootbox
- /score — show your score
- /top <nft|digi|gold|rate> — leaderboards

Admin commands (only ADMIN_ID)
- /nft_add <name> <price> <qty>
- /crypto_add <name> <price>
- /gift_add <name> <amount>
- /for <text> — broadcast to all registered players

Files used by the bot
- players.json — player profiles and balances
- nfts.json — NFT marketplace
- cryptos.json — crypto prices & histories
- gifts.json — gift definitions
- bank.json — bank balances & loans
- gold.json — gold price & history
- stars.json — stars balances

Security notes
- Never commit BOT_TOKEN to source. Use environment variables.
- If your token leaked, revoke it in BotFather and create a new one.
- ADMIN_ID should be a trusted numeric Telegram user id.

Production tips
- For more reliability, migrate JSON to a DB (SQLite / PostgreSQL).
- Add backups for JSON files before major operations.
- Consider adding monitoring/logging and tests (I can scaffold these).

Troubleshooting
- BOT_TOKEN missing: set environment variable.
- File write errors: run where the process can write files or set writable paths.

License
- MIT-like style: reuse and adapt. No warranty.

---

فارسی — خلاصه و راهنمای سریع
===========================

معرفی
- TeleBet یک ربات بازی/اقتصاد ساده برای تلگرام است که با فایل‌های JSON کار می‌کند.
- امکانات: امتیاز، طلا، ارز دیجیتال شبیه‌سازی‌شده، NFT، استارز، بانک و وام، جعبه شانس، لیدربورد و ابزار ادمین.

پیش‌نیازها
- Python 3.10 یا جدیدتر
- python-telegram-bot

نصب
```bash
pip install python-telegram-bot
```

راه‌اندازی
1. از BotFather در تلگرام توکن بگیرید.
2. متغیرهای محیطی را تنظیم کنید:
   - Linux/macOS:
     ```bash
     export BOT_TOKEN="<توکن-بات-شما>"
     export ADMIN_ID="<شناسه-تلگرام-عددی-ادمین>"   # اختیاری
     ```
   - Windows (PowerShell):
     ```powershell
     $env:BOT_TOKEN = "<توکن-بات-شما>"
     $env:ADMIN_ID = "<شناسه-تلگرام-عددی-ادمین>"
     ```
3. اجرا:
```bash
python main.py
```

دستورات اصلی (کاربر)
- /start — ثبت‌نام و خوش‌آمد
- /help — راهنما
- /bet <مقدار> <زوج|فرد> — شرط‌بندی
- /gold price | buy <amt> | sell <amt> — بازار طلا
- /crypto list | buy <name> <amt> | sell <name> <amt> | price <name> | portfolio
- /nft list | buy <name> | sell <name> [price] | portfolio
- /bank de <amt> | wi <amt> | ln <amt> | pr
- /stars buy <amt> | sell <amt>
- /box — باز کردن جعبه شانس
- /score — مشاهده امتیاز
- /top <nft|digi|gold|rate> — لیدربوردها

دستورات ادمین
- /nft_add <name> <price> <qty>
- /crypto_add <name> <price>
- /gift_add <name> <amount>
- /for <text> — ارسال پیام سراسری به کاربران ثبت‌شده.

فایل‌های برنامه
- players.json, nfts.json, cryptos.json, gifts.json, bank.json, gold.json, stars.json

نکات امنیتی
- توکن را در سورس نگه ندارید؛ از متغیر محیطی استفاده کنید.
- در صورت لو رفتن توکن، آن را با BotFather لغو و توکن جدید بسازید.
- ADMIN_ID را محافظت کنید.

گسترش و تولید
- برای محیط واقعی از DB به‌جای JSON استفاده کنید.
- اگر مایلید، من می‌توانم requirements.txt، فایل .gitignore، تست‌های پایه و یک workflow ساده برای CI آماده و کامیت کنم.

مشکلات رایج
- خطای BOT_TOKEN missing → متغیر محیطی را چک کنید.
- دسترسی به فایل‌ها → مسیر اجرا باید قابل نوشتن باشد.

---

If you want, I will also:
- Commit this README.md to the repository now.
- Add a requirements.txt and .gitignore.
- Scaffold a basic GitHub Actions workflow (lint/test).

Tell me which of the above extras you want me to add and I will apply them immediately.
