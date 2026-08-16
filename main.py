# بسم رب.
import asyncio
import sys

# پچ کردن asyncio برای جلوگیری از خطای event loop
if sys.version_info >= (3, 10):
    import asyncio
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
        
import json, random, datetime, asyncio, os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- فایل‌ها ---



PLAYERS_FILE = "players.json"
GIFTS_FILE = "gifts.json"
CRYPTOS_FILE = "cryptos.json"
BOOSTS_FILE = "boosts.json"
GOLD_FILE = "gold.json"

ADMIN_ID = 6627527892



# --- Load/Save JSON ---



def load_data(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)



# --- Player management ---



def get_player(user_id, username):
    players = load_data(PLAYERS_FILE)
    if str(user_id) not in players:
        players[str(user_id)] = {"username": username, "score": 50000, "gold": 0, "crypto": {}, "used_gifts": [], "boosts": [], "vip": False}
        save_data(PLAYERS_FILE, players)
    return players[str(user_id)]

def save_player(user_id, data):
    players = load_data(PLAYERS_FILE)
    players[str(user_id)] = data
    save_data(PLAYERS_FILE, players)



# --- Gold ---



LAST_GOLD_UPDATE = datetime.datetime.min
def update_gold_price():
    global LAST_GOLD_UPDATE
    now = datetime.datetime.now()
    if (now - LAST_GOLD_UPDATE).total_seconds() < 600:
        gold = load_data(GOLD_FILE)
        if not gold: gold = {"price":300000, "history":[]}
        return gold

    gold = load_data(GOLD_FILE)
    if not gold: gold = {"price":300000, "history":[]}

    change = random.randint(-100,100)
    new_price = max(gold.get("price",300000)+change, 1)
    gold["price"] = new_price

    # اضافه کردن به تاریخچه
    if "history" not in gold: gold["history"] = []
    gold["history"].append({"time": now.isoformat(), "price": new_price})
    if len(gold["history"]) > 10:  # نگه داشتن آخرین 10 تغییر
        gold["history"].pop(0)

    save_data(GOLD_FILE, gold)
    LAST_GOLD_UPDATE = now
    return gold
    
    
    
# - - - Gold Commands - - -


async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    gold_data = update_gold_price()

    if not context.args or context.args[0].lower() == "price":
        # نمایش قیمت فعلی طلا
        await update.message.reply_text(f"🪙 قیمت فعلی طلا: {gold_data['price']} امتیاز / گرم")
        return

    action = context.args[0].lower()
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ فرمت: /gold buy|sell <گرم>")
        return
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
        return

    total_price = amount * gold_data["price"]

    if action == "buy":
        if data["score"] < total_price:
            await update.message.reply_text("💀 امتیاز کافی برای خرید ندارید!")
            return
        data["score"] -= total_price
        data["gold"] += amount
        save_player(user.id, data)
        await update.message.reply_text(f"✅ خرید {amount} گرم طلا با {total_price} امتیاز انجام شد!")
    elif action == "sell":
        if data["gold"] < amount:
            await update.message.reply_text("💀 طلای کافی برای فروش ندارید!")
            return
        data["gold"] -= amount
        data["score"] += total_price
        save_player(user.id, data)
        await update.message.reply_text(f"✅ فروش {amount} گرم طلا با {total_price} امتیاز انجام شد!")
    else:
        await update.message.reply_text("⚠️ فرمت: /gold buy|sell <گرم>")



# --- Crypto ---


LAST_CRYPTO_UPDATE = datetime.datetime.min
def update_crypto_prices():
    global LAST_CRYPTO_UPDATE
    now = datetime.datetime.now()
    if (now - LAST_CRYPTO_UPDATE).total_seconds() < 600:
        return load_data(CRYPTOS_FILE)
    cryptos = load_data(CRYPTOS_FILE)
    for name, info in cryptos.items():
        change = random.uniform(-0.05,0.05)
        new_price = max(int(info["price"]*(1+change)),1)
        info["price"] = new_price
        info["history"].append({"time": now.isoformat(),"price":new_price})
        if len(info["history"])>10: info["history"].pop(0)
    save_data(CRYPTOS_FILE,cryptos)
    LAST_CRYPTO_UPDATE = now
    return cryptos



# --- Commands ---



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_player(user.id, user.username or user.first_name)
    await update.message.reply_text(f"سلام {user.first_name} به ربات شرط‌بندی تل‌نت خوش آمدید!.")



# --- Gifts ---


async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    gifts = load_data(GIFTS_FILE)
    if not context.args:
        await update.message.reply_text("⚠️ فرمت: /gift <نام هدیه>")
        return
    name = context.args[0].lower()
    if name not in gifts:
        await update.message.reply_text("💀 هدیه وجود ندارد!")
        return
    if name in data["used_gifts"]:
        await update.message.reply_text("💀 هدیه قبلا استفاده شده است!")
        return
    data["score"] += gifts[name]
    data["used_gifts"].append(name)
    save_player(user.id, data)
    await update.message.reply_text(f"✅ هدیه {name} دریافت شد! +{gifts[name]} امتیاز")

async def gift_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("💀 دسترسی ندارید!")
        return
    if len(context.args)<2:
        await update.message.reply_text("⚠️ فرمت: /gift add <name> <amount>")
        return
    name = context.args[0].lower()
    try: amount = int(context.args[1])
    except: 
        await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
        return
    gifts = load_data(GIFTS_FILE)
    gifts[name] = amount
    save_data(GIFTS_FILE,gifts)
    await update.message.reply_text(f"✅ هدیه {name} با مقدار {amount} اضافه شد!")



# - - - NFT - - -


NFT_FILE = "nfts.json"

async def nft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    nfts = load_data(NFT_FILE) or {}

    if not context.args:
        await update.message.reply_text(
            "⚠️ فرمت: /nft list / buy <name> / sell <name> / portfolio"
        )
        return

    cmd = context.args[0].lower()

    # لیست NFT ها
    if cmd == "list":
        if not nfts:
            await update.message.reply_text("📭 NFT موجودی نیست!")
            return

        msg = "🎨 NFT های موجود:\n\n"
        for name, info in nfts.items():
            msg += f"- {name}\n"
            msg += f"  - قیمت : {info['price']} امتیاز\n"
            msg += f"  - تعداد باقی مانده : {info['qty']}\n\n"

        await update.message.reply_text(msg)
        return

    # خرید NFT
    if cmd == "buy":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ فرمت: /nft buy <name>")
            return
        name = context.args[1]
        if name not in nfts or nfts[name]["qty"] <= 0:
            await update.message.reply_text("💀 این NFT موجود نیست یا تمام شده!")
            return
        price = nfts[name]["price"]
        if data["score"] < price:
            await update.message.reply_text("💀 امتیاز کافی برای خرید ندارید!")
            return

        data["score"] -= price
        data.setdefault("nfts", [])
        data["nfts"].append(name)
        nfts[name]["qty"] -= 1
        save_data(NFT_FILE, nfts)
        save_player(user.id, data)
        await update.message.reply_text(f"✅ شما NFT {name} را با {price} امتیاز خریدید!")
        return

    # فروش NFT
# فروش NFT با امکان تعیین قیمت
NFT_FILE = "nfts.json"
ADMIN_ID = 6627527892  # فقط ادمین اجازه داره

async def nft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    nfts = load_data(NFT_FILE) or {}

    if not context.args:
        await update.message.reply_text(
            "⚠️ فرمت: /nft list / buy <name> / sell <name> [price] / portfolio"
        )
        return

    cmd = context.args[0].lower()

    # لیست NFT ها
    if cmd == "list":
        if not nfts:
            await update.message.reply_text("📭 NFT موجودی نیست!")
            return
        msg = "🎨 NFT های موجود:\n\n"
        for name, info in nfts.items():
            msg += f"- {name}\n"
            msg += f"  - قیمت : {info['price']} امتیاز\n"
            msg += f"  - تعداد باقی مانده : {info['qty']}\n\n"
        await update.message.reply_text(msg)
        return

    # خرید NFT
    if cmd == "buy":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ فرمت: /nft buy <name>")
            return
        name = context.args[1]
        if name not in nfts or nfts[name]["qty"] <= 0:
            await update.message.reply_text("💀 این NFT موجود نیست یا تمام شده!")
            return
        price = nfts[name]["price"]
        if data["score"] < price:
            await update.message.reply_text("💀 امتیاز کافی برای خرید ندارید!")
            return
        data["score"] -= price
        data.setdefault("nfts", [])
        data["nfts"].append(name)
        nfts[name]["qty"] -= 1
        save_data(NFT_FILE, nfts)
        save_player(user.id, data)
        await update.message.reply_text(f"✅ شما NFT {name} را با {price} امتیاز خریدید!")
        return

    # فروش NFT با امکان تعیین قیمت دلخواه
    if cmd == "sell":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ فرمت: /nft sell <name> [price]")
            return
        name = context.args[1]
        if "nfts" not in data or name not in data["nfts"]:
            await update.message.reply_text("💀 شما این NFT را ندارید!")
            return

        # قیمت پیشنهادی توسط کاربر (در غیر این صورت قیمت پیش‌فرض)
        try:
            new_price = int(context.args[2]) if len(context.args) >= 3 else nfts.get(name, {"price": 0})["price"]
        except:
            await update.message.reply_text("⚠️ قیمت باید عدد باشد.")
            return

        # حذف از NFT های کاربر
        data["nfts"].remove(name)
        save_player(user.id, data)

        # اضافه کردن به بازار با پسوند player
        player_nft_name = f"{name}-player{user.id}"
        nfts[player_nft_name] = {"price": new_price, "qty": 1}
        save_data(NFT_FILE, nfts)

        await update.message.reply_text(
            f"✅ NFT {name} فروخته شد و به بازار اضافه شد ({player_nft_name}) با قیمت {new_price} امتیاز!"
        )
        return

    # پرتفوی کاربر
    if cmd == "portfolio":
        if "nfts" not in data or not data["nfts"]:
            await update.message.reply_text("📭 شما هیچ NFT ندارید!")
            return
        msg = "💼 NFT های شما:\n\n"
        for nft_name in data["nfts"]:
            price = nfts.get(nft_name, {"price": 0})["price"]
            msg += f"- {nft_name}: {price} امتیاز\n"
        await update.message.reply_text(msg)
        return

    await update.message.reply_text("⚠️ دستور نامعتبر!")


async def nft_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("💀 دسترسی ندارید!")
        return
    if len(context.args) < 3:
        await update.message.reply_text("⚠️ فرمت: /nft add <name> <price> <qty>")
        return
    name = context.args[0]
    try:
        price = int(context.args[1])
        qty = int(context.args[2])
    except:
        await update.message.reply_text("⚠️ قیمت و تعداد باید عدد باشند.")
        return
    nfts = load_data(NFT_FILE) or {}
    nfts[name] = {"price": price, "qty": qty}
    save_data(NFT_FILE, nfts)
    await update.message.reply_text(f"✅ NFT {name} با قیمت {price} و تعداد {qty} اضافه شد!")
    
    
# --- Crypto commands ---


async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    cryptos = update_crypto_prices()

    if not context.args:
        await update.message.reply_text(
            "⚠️ فرمت: /crypto list / buy <name> <amt> / sell <name> <amt> / price <name> / portfolio"
        )
        return

    cmd = context.args[0].lower()

    # لیست ارزها
    if cmd == "list":
        msg = "📈 ارزهای موجود:\n"
        for name, info in list(cryptos.items())[:20]:
            msg += f"- {name}: {info['price']} امتیاز\n"
        await update.message.reply_text(msg)
        return

    # قیمت یک ارز
    if cmd == "price":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ نام ارز را مشخص کنید.")
            return
        name = context.args[1]
        if name not in cryptos:
            await update.message.reply_text("💀 ارز موجود نیست!")
            return
        await update.message.reply_text(f"💹 قیمت فعلی {name}: {cryptos[name]['price']} امتیاز")
        return

    # خرید ارز
    if cmd == "buy":
        if len(context.args) < 3:
            await update.message.reply_text("⚠️ فرمت: /crypto buy <name> <amt>")
            return
        name = context.args[1]
        try:
            amt = int(context.args[2])
        except:
            await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
            return

        if name not in cryptos:
            await update.message.reply_text("💀 ارز موجود نیست!")
            return

        total_price = cryptos[name]["price"] * amt
        if data["score"] < total_price:
            await update.message.reply_text("💀 امتیاز کافی برای خرید ندارید!")
            return

        data["score"] -= total_price
        data.setdefault("cryptos", {})
        data["cryptos"][name] = data["cryptos"].get(name, 0) + amt
        save_player(user.id, data)
        await update.message.reply_text(f"✅ خرید {amt} عدد {name} با {total_price} امتیاز انجام شد!")
        return

    # فروش ارز
    if cmd == "sell":
        if len(context.args) < 3:
            await update.message.reply_text("⚠️ فرمت: /crypto sell <name> <amt>")
            return
        name = context.args[1]
        try:
            amt = int(context.args[2])
        except:
            await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
            return

        if name not in cryptos:
            await update.message.reply_text("💀 ارز موجود نیست!")
            return
        if "cryptos" not in data or data["cryptos"].get(name, 0) < amt:
            await update.message.reply_text("💀 شما این مقدار ارز ندارید!")
            return

        total_price = cryptos[name]["price"] * amt
        data["cryptos"][name] -= amt
        if data["cryptos"][name] == 0:
            del data["cryptos"][name]
        data["score"] += total_price
        save_player(user.id, data)
        await update.message.reply_text(f"✅ فروش {amt} عدد {name} با {total_price} امتیاز انجام شد!")
        return

    # پرتفوی کاربر
    if cmd == "portfolio":
        if "cryptos" not in data or not data["cryptos"]:
            await update.message.reply_text("📉 شما هیچ ارزی ندارید!")
            return
        msg = "💼 پرتفوی شما:\n"
        for name, amt in data["cryptos"].items():
            price = cryptos.get(name, {}).get("price", 0)
            msg += f"- {name}: {amt} عدد (قیمت فعلی: {price})\n"
        await update.message.reply_text(msg)
        return

    await update.message.reply_text("⚠️ دستور نامعتبر!")

    await update.message.reply_text("⚠️ دستور نامعتبر!")
async def crypto_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("💀 دسترسی ندارید!")
        return
    if len(context.args)<2:
        await update.message.reply_text("⚠️ فرمت: /crypto add <name> <price>")
        return
    name=context.args[0]
    try: price=int(context.args[1])
    except:
        await update.message.reply_text("⚠️ قیمت باید عدد باشد.")
        return
    cryptos=load_data(CRYPTOS_FILE)
    cryptos[name]={"price":price,"history":[]}
    save_data(CRYPTOS_FILE,cryptos)
    await update.message.reply_text(f"✅ ارز {name} با قیمت {price} اضافه شد!")



# --- Betting ---


async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    if not context.args:
        await update.message.reply_text("⚠️ فرمت: /bet <مقدار> <زوج/فرد>")
        return
    try:
        amount=int(context.args[0])
    except:
        await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
        return
    if amount>data["score"]:
        await update.message.reply_text("💀 امتیاز کافی ندارید!")
        return
    choice=context.args[1]
    result = random.choice(["زوج","فرد"])
    if choice==result:
        win = amount
        # Boost double_win
        if "double_win" in data.get("boosts",[]):
            win*=2
        data["score"]+=win
        await update.message.reply_text(f"🎉 بردید! نتیجه: {result} +{win} امتیاز")
    else:
        data["score"]-=amount
        await update.message.reply_text(f"💀 باختید! نتیجه: {result} -{amount} امتیاز")
    save_player(user.id,data)

# help command
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 دستورات ربات TeleBet | تل‌بت

🎲 Bet :
  /bet <Even/odd> <Amount>
  Ex: 
  /bet  زوج 1000

🎁 Gift :
  /gift <gift_name> - Use Gift 

💹 ارز دیجیتال:
  /crypto list - Crypto List
  /crypto buy <name> <amount> - Buy Crypto
  /crypto sell <name> <amount> - Sell Crypto
  /crypto price <name> - Crypto Price
  /top digi - Crypto LeaderBoard

🪙 Gold :
  /gold price - Current Gold Price
  /gold buy <amount> - Buy Gold
  /gold sell <amount> - Sell Gold
  /top gold - Gold LeaderBoard

🎨 NFT :
  /nft list - NFTs List
  /nft buy <name> - Buy NFT
  /nft sell <name> [price] - Sell NFT
  /nft portfolio - Your NFTs
  /top nft - NFT Owners LeaderBoard'

🏦 Bank And Loan :
  /bank de <Amount> Deposit
  /bank wi <Amount> - Withdraw
  /bank ln <Amount> - Loan (Max 1,000,000)
  /bank pr - Loan payment
  💸 نکته: وام‌ها با کارمزد 9٪ در صورت عدم پرداخت واریز از بانک کم می‌شوند

⭐ Stars : 
  /stars - Current Star Price
  /stars buy <Amount> - Buy Stars
  /stars sell <Amount> - Sell Stars

📊 Score and LeaderBoard :
  /score - Your Score
  /top rate - Score Leaderboard

"""
    await update.message.reply_text(help_text)
    
    
# - - - leaderboard - - -
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    players = load_data("players.json") or {}
    cryptos = load_data("cryptos.json") or {}

    if not context.args:
        await update.message.reply_text("⚠️ فرمت: /top nft|digi|gold|rate")
        return

    cmd = context.args[0].lower()

    if cmd == "nft":
        top = sorted(players.items(), key=lambda x: len(x[1].get("nfts", [])), reverse=True)[:10]
        msg = "🏆 Top NFT Holders:\n"
        for uid, data in top:
            msg += f"- {data.get('username','Unknown')}: {len(data.get('nfts',[]))} NFT\n"
        await update.message.reply_text(msg)

    elif cmd == "digi":
        def crypto_value(p):
            total = 0
            for name, amt in p.get("cryptos", {}).items():
                price = cryptos.get(name, {}).get("price", 0)
                total += price * amt
            return total

        top = sorted(players.items(), key=lambda x: crypto_value(x[1]), reverse=True)[:10]
        msg = "📈 Top Crypto Holders:\n"
        for uid, data in top:
            msg += f"- {data.get('username','Unknown')}: {crypto_value(data)} امتیاز\n"
        await update.message.reply_text(msg)

    elif cmd == "gold":
        top = sorted(players.items(), key=lambda x: x[1].get("gold",0), reverse=True)[:10]
        msg = "🏅 Top Gold Holders:\n"
        for uid, data in top:
            msg += f"- {data.get('username','Unknown')}: {data.get('gold',0)} گرم\n"
        await update.message.reply_text(msg)

    elif cmd == "rate":
        top = sorted(players.items(), key=lambda x: x[1].get("score",0), reverse=True)[:10]
        msg = "💰 Top Score:\n"
        for uid, data in top:
            msg += f"- {data.get('username','Unknown')}: {data.get('score',0)} امتیاز\n"
        await update.message.reply_text(msg)

    else:
        await update.message.reply_text("⚠️ فرمت: /top nft|digi|gold|rate")

# - - - Score - - -

async def my_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)  # تابع ذخیره/دریافت کاربر
    score = data.get("score", 0)
    await update.message.reply_text(f"💰 امتیاز فعلی شما: {score} ")
    
    
# - - - broadcast - - -
ADMIN_ID = 6627527892  # ادمین ربات

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("💀 دسترسی ندارید!")
        return

    if not context.args:
        await update.message.reply_text("⚠️ فرمت: /for متن پیام")
        return

    message_text = " ".join(context.args)
    players = load_data("players.json") or {}

    sent = 0
    for uid in players.keys():
        try:
            await context.bot.send_message(chat_id=int(uid), text=message_text)
            sent += 1
        except:
            continue

    await update.message.reply_text(f"✅ پیام به {sent} کاربر ارسال شد.")
    
# - - - Bank - - -

BANK_FILE = "bank.json"

def load_bank():
    if not os.path.exists(BANK_FILE):
        return {}
    with open(BANK_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_bank(data):
    with open(BANK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def apply_interest(user_id):
    bank = load_bank()
    now = datetime.datetime.now()
    user_bank = bank.get(str(user_id), {
        "balance": 0,
        "last_interest": now.isoformat(),
        "loan": 0
    })

    last_time = datetime.datetime.fromisoformat(user_bank.get("last_interest", now.isoformat()))
    diff = (now - last_time).total_seconds()

    # اگر بیشتر از 24 ساعت گذشته → سود بده
    if diff >= 86400:
        days = diff // 86400
        for _ in range(int(days)):
            user_bank["balance"] = int(user_bank["balance"] * 1.05)  # 5 درصد سود روزانه
        user_bank["last_interest"] = now.isoformat()

    # 📌 بررسی بدهی وام
    if user_bank["loan"] > 0 and user_bank["balance"] > 0:
        repay = int(user_bank["loan"] * 1.09)  # اصل + ۹٪ کارمزد
        if user_bank["balance"] >= repay:
            user_bank["balance"] -= repay
            user_bank["loan"] = 0

    bank[str(user_id)] = user_bank
    save_bank(bank)
    return user_bank

# 📌 دستور /bank
async def bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    data = get_player(user.id, user.username or user.first_name)

    bank = load_bank()
    user_bank = apply_interest(user_id)

    if not context.args:
        msg = f"🏦 موجودی بانک شما: {user_bank['balance']}\n💳 امتیاز فعلی: {data['score']}"
        if user_bank["loan"] > 0:
            msg += f"\n📉 بدهی وام: {user_bank['loan']}"
        await update.message.reply_text(msg)
        return

    cmd = context.args[0].lower()

    # 💰 واریز
    if cmd == "de":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ مقدار را وارد کنید.")
            return
        try:
            amt = int(context.args[1])
        except:
            await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
            return

        if data["score"] < amt:
            await update.message.reply_text("💀 امتیاز کافی ندارید!")
            return

        data["score"] -= amt
        user_bank["balance"] += amt
        save_player(user.id, data)

        bank[user_id] = user_bank
        save_bank(bank)
        await update.message.reply_text(
            f"✅ {amt} امتیاز به بانک واریز شد!\n🏦 موجودی بانک: {user_bank['balance']}"
        )

    # 💸 برداشت
    elif cmd == "wi":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ مقدار را وارد کنید.")
            return
        try:
            amt = int(context.args[1])
        except:
            await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
            return

        if user_bank["balance"] < amt:
            await update.message.reply_text("💀 موجودی بانک کافی نیست!")
            return

        user_bank["balance"] -= amt
        data["score"] += amt
        save_player(user.id, data)

        bank[user_id] = user_bank
        save_bank(bank)
        await update.message.reply_text(
            f"✅ {amt} امتیاز از بانک برداشت شد!\n🏦 موجودی بانک: {user_bank['balance']}"
        )

    # 🏦 گرفتن وام
    elif cmd == "ln":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ مقدار وام را وارد کنید.")
            return
        try:
            amt = int(context.args[1])
        except:
            await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
            return

        if amt > 1000000:
            await update.message.reply_text("💀 حداکثر وام 1,000,000 است!")
            return
        if user_bank["loan"] > 0:
            await update.message.reply_text("⚠️ شما یک وام پرداخت نشده دارید!")
            return

        data["score"] += amt
        user_bank["loan"] = amt
        save_player(user.id, data)

        bank[user_id] = user_bank
        save_bank(bank)
        await update.message.reply_text(
            f"💳 وام {amt} به شما داده شد!\n📉 بدهی فعلی: {user_bank['loan']}"
        )

    # 💳 پرداخت وام
    elif cmd == "pr":
        if user_bank["loan"] <= 0:
            await update.message.reply_text("✅ شما هیچ وامی ندارید!")
            return

        repay = int(user_bank["loan"] * 1.09)  # اصل + ۹٪
        if data["score"] < repay:
            await update.message.reply_text("💀 امتیاز کافی برای پرداخت وام ندارید!")
            return

        data["score"] -= repay
        user_bank["loan"] = 0
        save_player(user.id, data)

        bank[user_id] = user_bank
        save_bank(bank)
        await update.message.reply_text(
            f"✅ وام شما با کارمزد ۹٪ پرداخت شد!\n💳 از شما {repay} کسر شد."
        )

    else:
        await update.message.reply_text("⚠️ دستور نامعتبر!")

# - - - Stars - - -
STARS_FILE = "stars.json"
STAR_BASE_PRICE = 10000  # قیمت پایه هر استارز

async def stars(update, context):
    user = update.effective_user

    # توابع داخلی برای مدیریت stars
    def load_stars():
        try:
            with open(STARS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def save_stars(data):
        with open(STARS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_stars(user_id):
        stars = load_stars()
        return stars.get(str(user_id), 0)

    def set_stars(user_id, amount):
        stars = load_stars()
        stars[str(user_id)] = amount
        save_stars(stars)

    def get_star_price():
        import random, time
        random.seed(int(time.time() // 60))  # هر دقیقه تغییر کند
        change = random.randint(-500, 500)  # +/-500 امتیاز تغییر
        return max(1000, STAR_BASE_PRICE + change)  # حداقل 1000

    if not context.args:
        await update.message.reply_text(f"💫 قیمت فعلی هر استارز: {get_star_price()} امتیاز")
        return

    cmd = context.args[0].lower()
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ مقدار را وارد کنید.")
        return
    try:
        amt = int(context.args[1])
    except:
        await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
        return

    price = get_star_price()
    data = get_player(user.id, user.username or user.first_name)

    if cmd == "buy":
        total = price * amt
        if data["score"] < total:
            await update.message.reply_text(f"💀 امتیاز کافی برای خرید {amt} استارز ندارید! نیاز دارید {total} امتیاز.")
            return
        data["score"] -= total
        save_player(user.id, data)
        current = get_stars(user.id)
        set_stars(user.id, current + amt)
        await update.message.reply_text(f"✅ شما {amt} استارز خریدید!\n💫 موجودی شما: {current + amt} استارز")

    elif cmd == "sell":
        current = get_stars(user.id)
        if current < amt:
            await update.message.reply_text(f"💀 شما {amt} استارز ندارید!")
            return
        total = price * amt
        data["score"] += total
        save_player(user.id, data)
        set_stars(user.id, current - amt)
        await update.message.reply_text(f"✅ شما {amt} استارز فروختید!\n💸 دریافت {total} امتیاز\n💫 موجودی شما: {current - amt} استارز")

    else:
        await update.message.reply_text("⚠️ دستور نامعتبر! /stars buy <مقدار> یا /stars sell <مقدار>")
# - - - lootbox - - -
LOOTBOX_NFT = "gold-pepe"
LOOTBOX_COST_SCORE = 500  # هزینه باز کردن جعبه به امتیاز

async def lootbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)

    if data["score"] < LOOTBOX_COST_SCORE:
        await update.message.reply_text(f"💀 شما {LOOTBOX_COST_SCORE} امتیاز ندارید تا جعبه شانس را باز کنید!")
        return

    data["score"] -= LOOTBOX_COST_SCORE
    save_player(user.id, data)

    # انتخاب جایزه
    from random import randint, choice
    roll = randint(1, 100)

    if roll <= 60:  # 60٪ شانس برای 700 امتیاز
        prize = f"🎁 شما 700 امتیاز بردید!"
        data["score"] += 700
    elif roll <= 80:  # 20٪ شانس برای 1 TRX
        prize = f"🎁 شما 1 TRX بردید!"
        data.setdefault("cryptos", {})
        data["cryptos"]["TRX"] = data["cryptos"].get("TRX", 0) + 1
    elif roll <= 90:  # 10٪ شانس برای 1 استارز
        prize = f"🎁 شما 1 استارز بردید!"
        stars = load_data(STARS_FILE) or {}
        stars[str(user.id)] = stars.get(str(user.id), 0) + 1
        save_data(STARS_FILE, stars)
    elif roll <= 95:  # 5٪ شانس برای 1 طلا
        prize = f"🎁 شما 1 طلا بردید!"
        data.setdefault("gold", 0)
        data["gold"] += 1
    elif roll <= 99:  # 4٪ پوچ
        prize = "💀 هیچی نصیبتان نشد! بد شانس بودید!"
    else:  # 1٪ NFT
        prize = f"🎁 شما NFT {LOOTBOX_NFT} بردید!"
        data.setdefault("nfts", [])
        data["nfts"].append(LOOTBOX_NFT)

    save_player(user.id, data)
    await update.message.reply_text(prize)

# --- Main ---


app = ApplicationBuilder().token("8238495851:AAHhHRmTHRU2mUR7n7qtCJZcziyMUoqccew").build()

# - - - Normal Handlers - - -

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("bank", bank))
app.add_handler(CommandHandler("gift", gift))
app.add_handler(CommandHandler("crypto", crypto))
app.add_handler(CommandHandler("bet", bet))
app.add_handler(CommandHandler("box", lootbox))
app.add_handler(CommandHandler("help", help))
app.add_handler(CommandHandler("gold", gold))
app.add_handler(CommandHandler("nft", nft))
app.add_handler(CommandHandler("stars", stars))
app.add_handler(CommandHandler("score", my_score))
app.add_handler(CommandHandler("top", leaderboard))

# - - - Admin Handlers - - -

app.add_handler(CommandHandler("nft_add", nft_add))
app.add_handler(CommandHandler("crypto_add", crypto_add))
app.add_handler(CommandHandler("gift_add", gift_add))
app.add_handler(CommandHandler("for", broadcast))

# - - - Run - - -

if __name__=="__main__":
    import nest_asyncio
    nest_asyncio.apply()
    print("عشقم ران شد😏")
    app.run_polling()
