# -*- coding: utf-8 -*-
"""
TeleBet - Telegram betting game bot
Stage 1: translate remaining user-facing messages to English, update help text, register gold handler directly.
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
            pass


def load_data(path: str) -> Dict[str, Any]:
    _ensure_file(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_data(path: str, data: Any) -> None:
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
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
    await update.message.reply_text(f"Hello {user.first_name}, welcome to TeleBet!")


# --- Gifts ---


async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    gifts = load_data(GIFTS_FILE) or {}
    if not context.args:
        await update.message.reply_text("Usage: /gift <gift_name>")
        return
    name = context.args[0].lower()
    if name not in gifts:
        await update.message.reply_text("Gift not found.")
        return
    if name in data.get("used_gifts", []):
        await update.message.reply_text("You already used this gift.")
        return
    data["score"] = data.get("score", 0) + int(gifts[name])
    data.setdefault("used_gifts", []).append(name)
    save_player(user.id, data)
    await update.message.reply_text(f"Gift {name} redeemed! +{gifts[name]} points")


async def gift_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("Access denied.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /gift_add <name> <amount>")
        return
    name = context.args[0].lower()
    try:
        amount = int(context.args[1])
    except Exception:
        await update.message.reply_text("Amount must be an integer.")
        return
    gifts = load_data(GIFTS_FILE) or {}
    gifts[name] = amount
    save_data(GIFTS_FILE, gifts)
    await update.message.reply_text(f"Gift {name} added with amount {amount}.")


# --- NFT ---


async def nft(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    nfts = load_data(NFT_FILE) or {}

    if not context.args:
        await update.message.reply_text(
            "Usage: /nft list | /nft buy <name> | /nft sell <name> [price] | /nft portfolio"
        )
        return

    cmd = context.args[0].lower()

    if cmd == "list":
        if not nfts:
            await update.message.reply_text("No NFTs available.")
            return
        msg = "Available NFTs:\n\n"
        for name, info in nfts.items():
            msg += f"- {name}\n  - Price: {info.get('price', 0)} points\n  - Quantity: {info.get('qty', 0)}\n\n"
        await update.message.reply_text(msg)
        return

    if cmd == "buy":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /nft buy <name>")
            return
        name = context.args[1]
        if name not in nfts or nfts[name].get("qty", 0) <= 0:
            await update.message.reply_text("This NFT is not available or sold out.")
            return
        price = int(nfts[name].get("price", 0))
        if data.get("score", 0) < price:
            await update.message.reply_text("Not enough points to buy this NFT.")
            return
        data["score"] -= price
        data.setdefault("nfts", []).append(name)
        nfts[name]["qty"] = max(0, nfts[name].get("qty", 0) - 1)
        save_data(NFT_FILE, nfts)
        save_player(user.id, data)
        await update.message.reply_text(f"You bought NFT {name} for {price} points.")
        return

    if cmd == "sell":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /nft sell <name> [price]")
            return
        name = context.args[1]
        if "nfts" not in data or name not in data["nfts"]:
            await update.message.reply_text("You don't own this NFT.")
            return
        try:
            new_price = int(context.args[2]) if len(context.args) >= 3 else int(nfts.get(name, {}).get("price", 0))
        except Exception:
            await update.message.reply_text("Price must be an integer.")
            return
        data["nfts"].remove(name)
        save_player(user.id, data)
        player_nft_name = f"{name}-player{user.id}"
        nfts[player_nft_name] = {"price": new_price, "qty": 1}
        save_data(NFT_FILE, nfts)
        await update.message.reply_text(f"NFT {name} listed on market as {player_nft_name} for {new_price} points.")
        return

    if cmd == "portfolio":
        if "nfts" not in data or not data.get("nfts"):
            await update.message.reply_text("You have no NFTs.")
            return
        msg = "Your NFTs:\n\n"
        for nft_name in data.get("nfts", []):
            price = nfts.get(nft_name, {}).get("price", 0)
            msg += f"- {nft_name}: {price} points\n"
        await update.message.reply_text(msg)
        return

    await update.message.reply_text("Invalid NFT command.")


async def nft_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("Access denied.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /nft_add <name> <price> <qty>")
        return
    name = context.args[0]
    try:
        price = int(context.args[1])
        qty = int(context.args[2])
    except Exception:
        await update.message.reply_text("Price and quantity must be integers.")
        return
    nfts = load_data(NFT_FILE) or {}
    nfts[name] = {"price": price, "qty": qty}
    save_data(NFT_FILE, nfts)
    await update.message.reply_text(f"NFT {name} added: price={price}, qty={qty}.")


# --- Crypto commands ---


async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    cryptos = update_crypto_prices() or {}

    if not context.args:
        await update.message.reply_text(
            "Usage: /crypto list | /crypto buy <name> <amt> | /crypto sell <name> <amt> | /crypto price <name> | /crypto portfolio"
        )
        return

    cmd = context.args[0].lower()

    if cmd == "list":
        msg = "Available cryptos:\n"
        for name, info in list(cryptos.items())[:20]:
            msg += f"- {name}: {info.get('price', 0)} points\n"
        await update.message.reply_text(msg)
        return

    if cmd == "price":
        if len(context.args) < 2:
            await update.message.reply_text("Specify crypto name: /crypto price <name>")
            return
        name = context.args[1]
        if name not in cryptos:
            await update.message.reply_text("Crypto not found.")
            return
        await update.message.reply_text(f"Current price for {name}: {cryptos[name]['price']} points")
        return

    if cmd == "buy":
        if len(context.args) < 3:
            await update.message.reply_text("Usage: /crypto buy <name> <amt>")
            return
        name = context.args[1]
        try:
            amt = int(context.args[2])
        except Exception:
            await update.message.reply_text("Amount must be an integer.")
            return
        if name not in cryptos:
            await update.message.reply_text("Crypto not found.")
            return
        total_price = int(cryptos[name].get("price", 0)) * amt
        if data.get("score", 0) < total_price:
            await update.message.reply_text("Not enough points to buy.")
            return
        data["score"] -= total_price
        data.setdefault("cryptos", {})
        data["cryptos"][name] = data["cryptos"].get(name, 0) + amt
        save_player(user.id, data)
        await update.message.reply_text(f"Bought {amt} {name} for {total_price} points.")
        return

    if cmd == "sell":
        if len(context.args) < 3:
            await update.message.reply_text("Usage: /crypto sell <name> <amt>")
            return
        name = context.args[1]
        try:
            amt = int(context.args[2])
        except Exception:
            await update.message.reply_text("Amount must be an integer.")
            return
        if name not in cryptos:
            await update.message.reply_text("Crypto not found.")
            return
        if "cryptos" not in data or data.get("cryptos", {}).get(name, 0) < amt:
            await update.message.reply_text("You don't have that amount to sell.")
            return
        total_price = int(cryptos[name].get("price", 0)) * amt
        data["cryptos"][name] -= amt
        if data["cryptos"][name] == 0:
            del data["cryptos"][name]
        data["score"] += total_price
        save_player(user.id, data)
        await update.message.reply_text(f"Sold {amt} {name} for {total_price} points.")
        return

    if cmd == "portfolio":
        if "cryptos" not in data or not data.get("cryptos"):
            await update.message.reply_text("You have no cryptos.")
            return
        msg = "Your crypto portfolio:\n"
        for name, amt in data.get("cryptos", {}).items():
            price = cryptos.get(name, {}).get("price", 0)
            msg += f"- {name}: {amt} (current price: {price})\n"
        await update.message.reply_text(msg)
        return

    await update.message.reply_text("Invalid crypto command.")


# --- Betting ---


async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    if not context.args:
        await update.message.reply_text("Usage: /bet <amount> <even|odd>")
        return
    try:
        amount = int(context.args[0])
    except Exception:
        await update.message.reply_text("Amount must be an integer.")
        return
    if amount > data.get("score", 0):
        await update.message.reply_text("Not enough points to bet.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /bet <amount> <even|odd>")
        return
    choice = context.args[1].lower()
    if choice not in ("even", "odd"):
        await update.message.reply_text("Choice must be 'even' or 'odd'.")
        return
    result = random.choice(["even", "odd"])
    if choice == result:
        win = amount
        if "double_win" in data.get("boosts", []):
            win *= 2
        data["score"] += win
        await update.message.reply_text(f"You won! Result: {result} (+{win} points)")
    else:
        data["score"] -= amount
        await update.message.reply_text(f"You lost. Result: {result} (-{amount} points)")
    save_player(user.id, data)


# --- Help ---


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "TeleBet Bot Commands:\n\n"
        "Betting:\n  /bet <amount> <even|odd>\n\n"
        "Gifts:\n  /gift <gift_name>\n  /gift_add <name> <amount> (admin)\n\n"
        "Crypto:\n  /crypto list | buy <name> <amount> | sell <name> <amount> | price <name> | portfolio\n\n"
        "Gold:\n  /gold price | buy <amount> | sell <amount>\n\n"
        "NFTs:\n  /nft list | buy <name> | sell <name> [price] | portfolio\n  /nft_add <name> <price> <qty> (admin)\n\n"
        "Bank:\n  /bank de <amount> | wi <amount> | ln <amount> | pr\n\n"
        "Stars:\n  /stars buy <amount> | sell <amount> | price\n\n"
        "Score & Leaderboard:\n  /score | /top <nft|digi|gold|rate>\n\n"
        "Admin broadcast:\n  /for <message_text>\n"
    )
    await update.message.reply_text(help_text)


# --- Leaderboard ---


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    players = load_data(PLAYERS_FILE) or {}
    cryptos = load_data(CRYPTOS_FILE) or {}

    if not context.args:
        await update.message.reply_text("Usage: /top nft|digi|gold|rate")
        return

    cmd = context.args[0].lower()

    if cmd == "nft":
        top = sorted(players.items(), key=lambda x: len(x[1].get("nfts", [])), reverse=True)[:10]
        msg = "Top NFT Holders:\n"
        for uid, data in top:
            msg += f"- {data.get('username','Unknown')}: {len(data.get('nfts',[]))} NFT\n"
        await update.message.reply_text(msg)
        return

    if cmd == "digi":
        def crypto_value(p: Dict[str, Any]) -> int:
            total = 0
            for name, amt in p.get("cryptos", {}).items():
                try:
                    price = int(cryptos.get(name, {}).get("price", 0))
                    total += price * int(amt)
                except Exception:
                    continue
            return total

        top = sorted(players.items(), key=lambda x: crypto_value(x[1]), reverse=True)[:10]
        msg = "Top Crypto Holders:\n"
        for uid, data in top:
            msg += f"- {data.get('username','Unknown')}: {crypto_value(data)} points\n"
        await update.message.reply_text(msg)
        return

    if cmd == "gold":
        top = sorted(players.items(), key=lambda x: x[1].get("gold", 0), reverse=True)[:10]
        msg = "Top Gold Holders:\n"
        for uid, data in top:
            msg += f"- {data.get('username','Unknown')}: {data.get('gold',0)} g\n"
        await update.message.reply_text(msg)
        return

    if cmd == "rate":
        top = sorted(players.items(), key=lambda x: x[1].get("score", 0), reverse=True)[:10]
        msg = "Top Scores:\n"
        for uid, data in top:
            msg += f"- {data.get('username','Unknown')}: {data.get('score',0)} points\n"
        await update.message.reply_text(msg)
        return

    await update.message.reply_text("Usage: /top nft|digi|gold|rate")


# --- Score ---


async def my_score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = get_player(user.id, user.username or user.first_name)
    score = data.get("score", 0)
    await update.message.reply_text(f"Your current score: {score} points")


# --- Broadcast ---


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("Access denied.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /for <message_text>")
        return
    message_text = " ".join(context.args)
    players = load_data(PLAYERS_FILE) or {}
    sent = 0
    for uid in list(players.keys()):
        try:
            await context.bot.send_message(chat_id=int(uid), text=message_text)
            sent += 1
            await asyncio.sleep(0.02)
        except Exception:
            continue
    await update.message.reply_text(f"Broadcast sent to {sent} users.")


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
        msg = f"Bank balance: {user_bank.get('balance',0)}\nScore: {data.get('score',0)} points"
        if user_bank.get("loan", 0) > 0:
            msg += f"\nLoan: {user_bank.get('loan',0)}"
        await update.message.reply_text(msg)
        return

    cmd = context.args[0].lower()

    if cmd == "de":
        if len(context.args) < 2:
            await update.message.reply_text("Specify amount: /bank de <amount>")
            return
        try:
            amt = int(context.args[1])
        except Exception:
            await update.message.reply_text("Amount must be an integer.")
            return
        if data.get("score", 0) < amt:
            await update.message.reply_text("Not enough points.")
            return
        data["score"] -= amt
        user_bank["balance"] = user_bank.get("balance", 0) + amt
        save_player(user.id, data)
        bank_data = load_bank() or {}
        bank_data[user_id] = user_bank
        save_bank(bank_data)
        await update.message.reply_text(f"Deposited {amt} points. Bank balance: {user_bank['balance']}")
        return

    if cmd == "wi":
        if len(context.args) < 2:
            await update.message.reply_text("Specify amount: /bank wi <amount>")
            return
        try:
            amt = int(context.args[1])
        except Exception:
            await update.message.reply_text("Amount must be an integer.")
            return
        if user_bank.get("balance", 0) < amt:
            await update.message.reply_text("Insufficient bank balance.")
            return
        user_bank["balance"] -= amt
        data["score"] += amt
        save_player(user.id, data)
        bank_data = load_bank() or {}
        bank_data[user_id] = user_bank
        save_bank(bank_data)
        await update.message.reply_text(f"Withdrew {amt} points. Bank balance: {user_bank['balance']}")
        return

    if cmd == "ln":
        if len(context.args) < 2:
            await update.message.reply_text("Specify loan amount: /bank ln https://api.github.com/repos/iTs-GoJo/TeleBet/blob/main/main.py<amount>")
            return
