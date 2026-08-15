# -*- coding: utf-8 -*-
"""
TeleBet - Telegram betting game bot
Updated main.py: cleaned duplicate code, fixed bugs, and moved sensitive token to environment variable.
Requirements:
 - python 3.10+
 - python-telegram-bot v20+

Usage:
 - Set environment variable BOT_TOKEN to your Telegram bot token.
 - Optionally set ADMIN_ID to the Telegram user id of the admin.
 - Run: python main.py

This file was refactored to:
 - Remove duplicated functions and constants
 - Ensure data loading/saving is robust
 - Avoid hard-coded token in source
 - Handle missing data files gracefully
"""

from __future__ import annotations

import os
import sys
import json
import random
import datetime
import asyncio
from typing import Dict, Any

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Config / Files ---
PLAYERS_FILE = "players.json"
GIFTS_FILE = "gifts.json"
CRYPTOS_FILE = "cryptos.json"
BOOSTS_FILE = "boosts.json"
GOLD_FILE = "gold.json"
NFT_FILE = "nfts.json"
BANK_FILE = "bank.json"
STARS_FILE = "stars.json"

# Read admin id and bot token from environment for security
ADMIN_ID = int(os.getenv("ADMIN_ID", "6627527892"))
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Helpers: load/save JSON ---

def _ensure_file(path: str, default: Any = None) -> None:
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default if default is not None else {}, f, ensure_ascii=False, indent=2)
        except Exception:
            # ignore - file creation best-effort
            pass


def load_data(path: str) -> Dict[str, Any]:
    _ensure_file(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # always return a dict for our storage files
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_data(path: str, data: Any) -> None:
    # create parent file if missing
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        # try to create directory then retry
        d = os.path.dirname(path)
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass


# --- Player management ---

def get_player(user_id: int, username: str) -> Dict[str, Any]:
    players = load_data(PLAYERS_FILE)
    key = str(user_id)
    if key not in players:
        players[key] = {
            "username": username,
            "score": 50000,
            "gold": 0,
            "cryptos": {},
            "used_gifts": [],
            "boosts": [],
            "vip": False,
            "nfts": [],
        }
        save_data(PLAYERS_FILE, players)
    return players[key]


def save_player(user_id: int, data: Dict[str, Any]) -> None:
    players = load_data(PLAYERS_FILE)
    players[str(user_id)] = data
    save_data(PLAYERS_FILE, players)


# --- Gold price simulator ---
LAST_GOLD_UPDATE = datetime.datetime.min


def update_gold_price() -> Dict[str, Any]:
    global LAST_GOLD_UPDATE
    now = datetime.datetime.now()
    # cache for 10 minutes
    if (now - LAST_GOLD_UPDATE).total_seconds() < 600:
        gold = load_data(GOLD_FILE)
        if not gold:
            gold = {"price": 300000, "history": []}
        return gold

    gold = load_data(GOLD_FILE)
    if not gold:
        gold = {"price": 300000, "history": []}

    change = random.randint(-100, 100)
    new_price = max(gold.get("price", 300000) + change, 1)
    gold["price"] = new_price

    gold.setdefault("history", [])
    gold["history"].append({"time": now.isoformat(), "price": new_price})
    if len(gold["history"]) > 10:
        gold["history"].pop(0)

    save_data(GOLD_FILE, gold)
    LAST_GOLD_UPDATE = now
    return gold


# --- Crypto price simulator ---
LAST_CRYPTO_UPDATE = datetime.datetime.min


def update_crypto_prices() -> Dict[str, Any]:
    global LAST_CRYPTO_UPDATE
    now = datetime.datetime.now()
    cryptos = load_data(CRYPTOS_FILE) or {}
    # cache 10 minutes
    if (now - LAST_CRYPTO_UPDATE).total_seconds() < 600:
        return cryptos

    for name, info in list(cryptos.items()):
        try:
            change = random.uniform(-0.05, 0.05)
            price = int(info.get("price", 1) * (1 + change))
            price = max(price, 1)
            info["price"] = price
            info.setdefault("history", [])
            info["history"].append({"time": now.isoformat(), "price": price})
            if len(info["history"]) > 10:
                info["history"].pop(0)
        except Exception:
            continue

    save_data(CRYPTOS_FILE, cryptos)
    LAST_CRYPTO_UPDATE = now
    return cryptos


# --- Commands ---


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    get_player(user.id, user.username or user.first_name)
    await update.message.reply_text(f"سلام {user.first_name} به ربات شرط‌بندی خوش آمدید! 🇮🇷")


# --- Gifts ---


async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    gifts = load_data(GIFTS_FILE) or {}
    if not context.args:
        await update.message.reply_text("⚠️ فرمت: /gift <نام هدیه>")
        return
    name = context.args[0].lower()
    if name not in gifts:
        await update.message.reply_text("💀 هدیه وجود ندارد!")
        return
    if name in data.get("used_gifts", []):
        await update.message.reply_text("💀 هدیه قبلا استفاده شده است!")
        return
    data["score"] = data.get("score", 0) + int(gifts[name])
    data.setdefault("used_gifts", []).append(name)
    save_player(user.id, data)
    await update.message.reply_text(f"✅ هدیه {name} دریافت شد! +{gifts[name]} امتیاز")


async def gift_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("💀 دسترسی ندارید!")
        return
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ فرمت: /gift add <name> <amount>")
        return
    name = context.args[0].lower()
    try:
        amount = int(context.args[1])
    except Exception:
        await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
        return
    gifts = load_data(GIFTS_FILE) or {}
    gifts[name] = amount
    save_data(GIFTS_FILE, gifts)
    await update.message.reply_text(f"✅ هدیه {name} با مقدار {amount} اضافه شد!")


# --- NFT ---


async def nft(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    nfts = load_data(NFT_FILE) or {}

    if not context.args:
        await update.message.reply_text(
            "⚠️ فرمت: /nft list | /nft buy <name> | /nft sell <name> [price] | /nft portfolio"
        )
        return

    cmd = context.args[0].lower()

    if cmd == "list":
        if not nfts:
            await update.message.reply_text("📭 NFT موجودی نیست!")
            return
        msg = "🎨 NFT های موجود:\n\n"
        for name, info in nfts.items():
            msg += f"- {name}\n  - قیمت : {info.get('price', 0)} امتیاز\n  - تعداد باقی مانده : {info.get('qty', 0)}\n\n"
        await update.message.reply_text(msg)
        return

    if cmd == "buy":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ فرمت: /nft buy <name>")
            return
        name = context.args[1]
        if name not in nfts or nfts[name].get("qty", 0) <= 0:
            await update.message.reply_text("💀 این NFT موجود نیست یا تمام شده!")
            return
        price = int(nfts[name].get("price", 0))
        if data.get("score", 0) < price:
            await update.message.reply_text("💀 امتیاز کافی برای خرید ندارید!")
            return
        data["score"] -= price
        data.setdefault("nfts", []).append(name)
        nfts[name]["qty"] = max(0, nfts[name].get("qty", 0) - 1)
        save_data(NFT_FILE, nfts)
        save_player(user.id, data)
        await update.message.reply_text(f"✅ شما NFT {name} را با {price} امتیاز خریدید!")
        return

    if cmd == "sell":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ فرمت: /nft sell <name> [price]")
            return
        name = context.args[1]
        if "nfts" not in data or name not in data["nfts"]:
            await update.message.reply_text("💀 شما این NFT را ندارید!")
            return
        try:
            new_price = int(context.args[2]) if len(context.args) >= 3 else int(nfts.get(name, {}).get("price", 0))
        except Exception:
            await update.message.reply_text("⚠️ قیمت باید عدد باشد.")
            return
        # remove from user
        data["nfts"].remove(name)
        save_player(user.id, data)
        # add to market with player suffix
        player_nft_name = f"{name}-player{user.id}"
        nfts[player_nft_name] = {"price": new_price, "qty": 1}
        save_data(NFT_FILE, nfts)
        await update.message.reply_text(
            f"✅ NFT {name} فروخته شد و به بازار اضافه شد ({player_nft_name}) با قیمت {new_price} امتیاز!"
        )
        return

    if cmd == "portfolio":
        if "nfts" not in data or not data.get("nfts"):
            await update.message.reply_text("📭 شما هیچ NFT ندارید!")
            return
        msg = "💼 NFT های شما:\n\n"
        for nft_name in data.get("nfts", []):
            price = nfts.get(nft_name, {}).get("price", 0)
            msg += f"- {nft_name}: {price} امتیاز\n"
        await update.message.reply_text(msg)
        return

    await update.message.reply_text("⚠️ دستور نامعتبر!")


async def nft_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    except Exception:
        await update.message.reply_text("⚠️ قیمت و تعداد باید عدد باشند.")
        return
    nfts = load_data(NFT_FILE) or {}
    nfts[name] = {"price": price, "qty": qty}
    save_data(NFT_FILE, nfts)
    await update.message.reply_text(f"✅ NFT {name} با قیمت {price} و تعداد {qty} اضافه شد!")


# --- Crypto commands ---


async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    cryptos = update_crypto_prices() or {}

    if not context.args:
        await update.message.reply_text(
            "⚠️ فرمت: /crypto list | /crypto buy <name> <amt> | /crypto sell <name> <amt> | /crypto price <name> | /crypto portfolio"
        )
        return

    cmd = context.args[0].lower()

    if cmd == "list":
        msg = "📈 ارزهای موجود:\n"
        for name, info in list(cryptos.items())[:20]:
            msg += f"- {name}: {info.get('price', 0)} امتیاز\n"
        await update.message.reply_text(msg)
        return

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

    if cmd == "buy":
        if len(context.args) < 3:
            await update.message.reply_text("⚠️ فرمت: /crypto buy <name> <amt>")
            return
        name = context.args[1]
        try:
            amt = int(context.args[2])
        except Exception:
            await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
            return
        if name not in cryptos:
            await update.message.reply_text("💀 ارز موجود نیست!")
            return
        total_price = int(cryptos[name].get("price", 0)) * amt
        if data.get("score", 0) < total_price:
            await update.message.reply_text("💀 امتیاز کافی برای خرید ندارید!")
            return
        data["score"] -= total_price
        data.setdefault("cryptos", {})
        data["cryptos"][name] = data["cryptos"].get(name, 0) + amt
        save_player(user.id, data)
        await update.message.reply_text(f"✅ خرید {amt} عدد {name} با {total_price} امتیاز انجام شد!")
        return

    if cmd == "sell":
        if len(context.args) < 3:
            await update.message.reply_text("⚠️ فرمت: /crypto sell <name> <amt>")
            return
        name = context.args[1]
        try:
            amt = int(context.args[2])
        except Exception:
            await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
            return
        if name not in cryptos:
            await update.message.reply_text("💀 ارز موجود نیست!")
            return
        if "cryptos" not in data or data.get("cryptos", {}).get(name, 0) < amt:
            await update.message.reply_text("💀 شما این مقدار ارز ندارید!")
            return
        total_price = int(cryptos[name].get("price", 0)) * amt
        data["cryptos"][name] -= amt
        if data["cryptos"][name] == 0:
            del data["cryptos"][name]
        data["score"] += total_price
        save_player(user.id, data)
        await update.message.reply_text(f"✅ فروش {amt} عدد {name} با {total_price} امتیاز انجام شد!")
        return

    if cmd == "portfolio":
        if "cryptos" not in data or not data.get("cryptos"):
            await update.message.reply_text("📉 شما هیچ ارزی ندارید!")
            return
        msg = "💼 پرتفوی شما:\n"
        for name, amt in data.get("cryptos", {}).items():
            price = cryptos.get(name, {}).get("price", 0)
            msg += f"- {name}: {amt} عدد (قیمت فعلی: {price})\n"
        await update.message.reply_text(msg)
        return

    await update.message.reply_text("⚠️ دستور نامعتبر!")


# --- Betting ---


async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    if not context.args:
        await update.message.reply_text("⚠️ فرمت: /bet <مقدار> <زوج/فرد>")
        return
    try:
        amount = int(context.args[0])
    except Exception:
        await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
        return
    if amount > data.get("score", 0):
        await update.message.reply_text("💀 امتیاز کافی ندارید!")
        return
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ فرمت: /bet <مقدار> <زوج/فرد>")
        return
    choice = context.args[1]
    result = random.choice(["زوج", "فرد"])
    if choice == result:
        win = amount
        if "double_win" in data.get("boosts", []):
            win *= 2
        data["score"] += win
        await update.message.reply_text(f"🎉 بردید! نتیجه: {result} +{win} امتیاز")
    else:
        data["score"] -= amount
        await update.message.reply_text(f"💀 باختید! نتیجه: {result} -{amount} امتیاز")
    save_player(user.id, data)


# --- Help ---


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🤖 دستورات ربات TeleBet | تل‌بت\n\n"
        "🎲 شرط‌بندی:\n  /bet <مقدار> <زوج/فرد>\n\n"
        "🎁 هدایا:\n  /gift <gift_name>\n\n"
        "💹 ارز دیجیتال:\n  /crypto list | buy <name> <amount> | sell <name> <amount> | price <name> | portfolio\n\n"
        "🪙 طلا:\n  /gold price | buy <amount> | sell <amount>\n\n"
        "🎨 ان‌اف‌تی:\n  /nft list | buy <name> | sell <name> [price] | portfolio\n\n"
        "🏦 بانک و وام:\n  /bank de <مقدار> | wi <مقدار> | ln <مقدار> | pr\n\n"
        "💫 استارز:\n  /stars buy <مقدار> | sell <مقدار> | price\n\n"
        "📊 امتیاز و لیدربورد:\n  /score | /top <nft|digi|gold|rate>\n"
    )
    await update.message.reply_text(help_text)


# --- Leaderboard ---


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    players = load_data(PLAYERS_FILE) or {}
    cryptos = load_data(CRYPTOS_FILE) or {}

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
        return

    if cmd == "digi":
        def crypto_value(p: Dict[str, Any]) -> int:
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
        return

    if cmd == "gold":
        top = sorted(players.items(), key=lambda x: x[1].get("gold", 0), reverse=True)[:10]
        msg = "🏅 Top Gold Holders:\n"
        for uid, data in top:
            msg += f"- {data.get('username','Unknown')}: {data.get('gold',0)} گرم\n"
        await update.message.reply_text(msg)
        return

    if cmd == "rate":
        top = sorted(players.items(), key=lambda x: x[1].get("score", 0), reverse=True)[:10]
        msg = "💰 Top Score:\n"
        for uid, data in top:
            msg += f"- {data.get('username','Unknown')}: {data.get('score',0)} امتیاز\n"
        await update.message.reply_text(msg)
        return

    await update.message.reply_text("⚠️ فرمت: /top nft|digi|gold|rate")


# --- Score ---


async def my_score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    score = data.get("score", 0)
    await update.message.reply_text(f"💰 امتیاز فعلی شما: {score}")


# --- Broadcast ---


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("💀 دسترسی ندارید!")
        return
    if not context.args:
        await update.message.reply_text("⚠️ فرمت: /for متن پیام")
        return
    message_text = " ".join(context.args)
    players = load_data(PLAYERS_FILE) or {}
    sent = 0
    for uid in players.keys():
        try:
            await context.bot.send_message(chat_id=int(uid), text=message_text)
            sent += 1
        except Exception:
            continue
    await update.message.reply_text(f"✅ پیام به {sent} کاربر ارسال شد.")


# --- Bank ---


def load_bank() -> Dict[str, Any]:
    return load_data(BANK_FILE)


def save_bank(data: Dict[str, Any]) -> None:
    save_data(BANK_FILE, data)


def apply_interest(user_id: str) -> Dict[str, Any]:
    bank = load_bank() or {}
    now = datetime.datetime.now()
    user_bank = bank.get(str(user_id), {"balance": 0, "last_interest": now.isoformat(), "loan": 0})
    try:
        last_time = datetime.datetime.fromisoformat(user_bank.get("last_interest", now.isoformat()))
    except Exception:
        last_time = now
    diff = (now - last_time).total_seconds()

    if diff >= 86400:
        days = int(diff // 86400)
        for _ in range(days):
            user_bank["balance"] = int(user_bank.get("balance", 0) * 1.05)
        user_bank["last_interest"] = now.isoformat()

    if user_bank.get("loan", 0) > 0 and user_bank.get("balance", 0) > 0:
        repay = int(user_bank.get("loan", 0) * 1.09)
        if user_bank.get("balance", 0) >= repay:
            user_bank["balance"] -= repay
            user_bank["loan"] = 0

    bank[str(user_id)] = user_bank
    save_bank(bank)
    return user_bank


async def bank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    data = get_player(user.id, user.username or user.first_name)
    user_bank = apply_interest(user_id)

    if not context.args:
        msg = f"🏦 موجودی بانک شما: {user_bank.get('balance',0)}\n💳 امتیاز فعلی: {data.get('score',0)}"
        if user_bank.get("loan", 0) > 0:
            msg += f"\n📉 بدهی وام: {user_bank.get('loan',0)}"
        await update.message.reply_text(msg)
        return

    cmd = context.args[0].lower()

    if cmd == "de":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ مقدار را وارد کنید.")
            return
        try:
            amt = int(context.args[1])
        except Exception:
            await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
            return
        if data.get("score", 0) < amt:
            await update.message.reply_text("💀 امتیاز کافی ندارید!")
            return
        data["score"] -= amt
        user_bank["balance"] = user_bank.get("balance", 0) + amt
        save_player(user.id, data)
        bank_data = load_bank() or {}
        bank_data[user_id] = user_bank
        save_bank(bank_data)
        await update.message.reply_text(f"✅ {amt} امتیاز به بانک واریز شد!\n🏦 موجودی بانک: {user_bank['balance']}")
        return

    if cmd == "wi":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ مقدار را وارد کنید.")
            return
        try:
            amt = int(context.args[1])
        except Exception:
            await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
            return
        if user_bank.get("balance", 0) < amt:
            await update.message.reply_text("💀 موجودی بانک کافی نیست!")
            return
        user_bank["balance"] -= amt
        data["score"] += amt
        save_player(user.id, data)
        bank_data = load_bank() or {}
        bank_data[user_id] = user_bank
        save_bank(bank_data)
        await update.message.reply_text(f"✅ {amt} امتیاز از بانک برداشت شد!\n🏦 موجودی بانک: {user_bank['balance']}")
        return

    if cmd == "ln":
        if len(context.args) < 2:
            await update.message.reply_text("⚠️ مقدار وام را وارد کنید.")
            return
        try:
            amt = int(context.args[1])
        except Exception:
            await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
            return
        if amt > 1000000:
            await update.message.reply_text("💀 حداکثر وام 1,000,000 است!")
            return
        if user_bank.get("loan", 0) > 0:
            await update.message.reply_text("⚠️ شما یک وام پرداخت نشده دارید!")
            return
        data["score"] += amt
        user_bank["loan"] = amt
        save_player(user.id, data)
        bank_data = load_bank() or {}
        bank_data[user_id] = user_bank
        save_bank(bank_data)
        await update.message.reply_text(f"💳 وام {amt} به شما داده شد!\n📉 بدهی فعلی: {user_bank['loan']}")
        return

    if cmd == "pr":
        if user_bank.get("loan", 0) <= 0:
            await update.message.reply_text("✅ شما هیچ وامی ندارید!")
            return
        repay = int(user_bank.get("loan", 0) * 1.09)
        if data.get("score", 0) < repay:
            await update.message.reply_text("💀 امتیاز کافی برای پرداخت وام ندارید!")
            return
        data["score"] -= repay
        user_bank["loan"] = 0
        save_player(user.id, data)
        bank_data = load_bank() or {}
        bank_data[user_id] = user_bank
        save_bank(bank_data)
        await update.message.reply_text(f"✅ وام شما با کارمزد ۹٪ پرداخت شد!\n💳 از شما {repay} کسر شد.")
        return

    await update.message.reply_text("⚠️ دستور نامعتبر!")


# --- Stars ---
STAR_BASE_PRICE = 10000


async def stars(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    def load_stars() -> Dict[str, int]:
        return load_data(STARS_FILE) or {}

    def save_stars(data: Dict[str, int]) -> None:
        save_data(STARS_FILE, data)

    def get_stars(user_id: int) -> int:
        stars = load_stars()
        return int(stars.get(str(user_id), 0))

    def set_stars(user_id: int, amount: int) -> None:
        stars = load_stars()
        stars[str(user_id)] = amount
        save_stars(stars)

    def get_star_price() -> int:
        import time
        random.seed(int(time.time() // 60))
        change = random.randint(-500, 500)
        return max(1000, STAR_BASE_PRICE + change)

    if not context.args:
        await update.message.reply_text(f"💫 قیمت فعلی هر استارز: {get_star_price()} امتیاز")
        return

    cmd = context.args[0].lower()
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ مقدار را وارد کنید.")
        return
    try:
        amt = int(context.args[1])
    except Exception:
        await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
        return

    price = get_star_price()
    data = get_player(user.id, user.username or user.first_name)

    if cmd == "buy":
        total = price * amt
        if data.get("score", 0) < total:
            await update.message.reply_text(f"💀 امتیاز کافی برای خرید {amt} استارز ندارید! نیاز دارید {total} امتیاز.")
            return
        data["score"] -= total
        save_player(user.id, data)
        current = get_stars(user.id)
        set_stars(user.id, current + amt)
        await update.message.reply_text(f"✅ شما {amt} استارز خریدید!\n💫 موجودی شما: {current + amt} استارز")
        return

    if cmd == "sell":
        current = get_stars(user.id)
        if current < amt:
            await update.message.reply_text(f"💀 شما {amt} استارز ندارید!")
            return
        total = price * amt
        data["score"] += total
        save_player(user.id, data)
        set_stars(user.id, current - amt)
        await update.message.reply_text(f"✅ شما {amt} استارز فروختید!\n💸 دریافت {total} امتیاز\n💫 موجودی شما: {current - amt} استارز")
        return

    await update.message.reply_text("⚠️ دستور نامعتبر! /stars buy <مقدار> یا /stars sell <مقدار>")


# --- Lootbox ---
LOOTBOX_NFT = "gold-pepe"
LOOTBOX_COST_SCORE = 500


async def lootbox(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    if data.get("score", 0) < LOOTBOX_COST_SCORE:
        await update.message.reply_text(f"💀 شما {LOOTBOX_COST_SCORE} امتیاز ندارید تا جعبه شانس را باز کنید!")
        return
    data["score"] -= LOOTBOX_COST_SCORE
    from random import randint
    roll = randint(1, 100)
    prize = ""
    if roll <= 60:
        prize = "🎁 شما 700 امتیاز بردید!"
        data["score"] += 700
    elif roll <= 80:
        prize = "🎁 شما 1 TRX بردید!"
        data.setdefault("cryptos", {})
        data["cryptos"]["TRX"] = data["cryptos"].get("TRX", 0) + 1
    elif roll <= 90:
        prize = "🎁 شما 1 استارز بردید!"
        stars = load_data(STARS_FILE) or {}
        stars[str(user.id)] = stars.get(str(user.id), 0) + 1
        save_data(STARS_FILE, stars)
    elif roll <= 95:
        prize = "🎁 شما 1 طلا بردید!"
        data.setdefault("gold", 0)
        data["gold"] += 1
    elif roll <= 99:
        prize = "💀 هیچی نصیبتان نشد! بد شانس بودید!"
    else:
        prize = f"🎁 شما NFT {LOOTBOX_NFT} بردید!"
        data.setdefault("nfts", [])
        data["nfts"].append(LOOTBOX_NFT)
    save_player(user.id, data)
    await update.message.reply_text(prize)


# --- App init and handlers ---


def _ensure_token_or_exit() -> str:
    if not BOT_TOKEN:
        print("ERROR: BOT_TOKEN environment variable is not set. Set it and restart.")
        sys.exit(1)
    return BOT_TOKEN


def main() -> None:
    token = _ensure_token_or_exit()

    # allow nested event loop in some environments (not harmful)
    try:
        import nest_asyncio

        nest_asyncio.apply()
    except Exception:
        pass

    app = ApplicationBuilder().token(token).build()

    # Normal handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bank", bank))
    app.add_handler(CommandHandler("gift", gift))
    app.add_handler(CommandHandler("crypto", crypto))
    app.add_handler(CommandHandler("bet", bet))
    app.add_handler(CommandHandler("box", lootbox))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("gold", lambda u, c: gold_cmd(u, c)))
    app.add_handler(CommandHandler("nft", nft))
    app.add_handler(CommandHandler("stars", stars))
    app.add_handler(CommandHandler("score", my_score))
    app.add_handler(CommandHandler("top", leaderboard))

    # Admin handlers
    app.add_handler(CommandHandler("nft_add", nft_add))
    app.add_handler(CommandHandler("crypto_add", crypto_add))
    app.add_handler(CommandHandler("gift_add", gift_add))
    app.add_handler(CommandHandler("for", broadcast))

    print("Bot is running...")
    app.run_polling()


# --- Gold command adapter (keeps original behavior) ---
async def gold_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # original gold command implementation moved here to avoid forward-ref issues
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    gold_data = update_gold_price()

    if not context.args or (len(context.args) > 0 and context.args[0].lower() == "price"):
        await update.message.reply_text(f"🪙 قیمت فعلی طلا: {gold_data.get('price', 0)} امتیاز / گرم")
        return

    action = context.args[0].lower()
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ فرمت: /gold buy|sell <گرم>")
        return
    try:
        amount = int(context.args[1])
    except Exception:
        await update.message.reply_text("⚠️ مقدار باید عدد باشد.")
        return

    total_price = amount * gold_data.get("price", 0)
    if action == "buy":
        if data.get("score", 0) < total_price:
            await update.message.reply_text("💀 امتیاز کافی برای خرید ندارید!")
            return
        data["score"] -= total_price
        data["gold"] = data.get("gold", 0) + amount
        save_player(user.id, data)
        await update.message.reply_text(f"✅ خرید {amount} گرم طلا با {total_price} امتیاز انجام شد!")
    elif action == "sell":
        if data.get("gold", 0) < amount:
            await update.message.reply_text("💀 طلای کافی برای فروش ندارید!")
            return
        data["gold"] -= amount
        data["score"] += total_price
        save_player(user.id, data)
        await update.message.reply_text(f"✅ فروش {amount} گرم طلا با {total_price} امتیاز انجام شد!")
    else:
        await update.message.reply_text("⚠️ فرمت: /gold buy|sell <گرم>")


# --- Admin crypto_add (kept signature) ---
async def crypto_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("💀 دسترسی ندارید!")
        return
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ فرمت: /crypto add <name> <price>")
        return
    name = context.args[0]
    try:
        price = int(context.args[1])
    except Exception:
        await update.message.reply_text("⚠️ قیمت باید عدد باشد.")
        return
    cryptos = load_data(CRYPTOS_FILE) or {}
    cryptos[name] = {"price": price, "history": []}
    save_data(CRYPTOS_FILE, cryptos)
    await update.message.reply_text(f"✅ ارز {name} با قیمت {price} اضافه شد!")


if __name__ == "__main__":
    main()
