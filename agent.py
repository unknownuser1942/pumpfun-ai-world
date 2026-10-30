#!/usr/bin/env python3
"""
Pump.fun AI World — autonomous paper-trading agent.
Streams new tokens, scores them with multi-factor logic, manages positions
with simulated take-profit / stop-loss, and persists state.
HIGH RISK. Most tokens go to zero. Paper mode only by default.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

try:
    import websockets
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("Missing deps. Run: pip install -r requirements.txt")
    sys.exit(1)

load_dotenv()

# ===================== CONFIG =====================
CONFIG = {
    "PAPER_TRADING": os.getenv("PAPER_TRADING", "true").lower() == "true",
    "BUY_AMOUNT_SOL": float(os.getenv("BUY_AMOUNT_SOL", "0.01")),
    "SLIPPAGE": int(os.getenv("SLIPPAGE", "15")),
    "PRIORITY_FEE": float(os.getenv("PRIORITY_FEE", "0.00005")),
    "KEYWORDS": [k.strip() for k in os.getenv("KEYWORDS", "dog,cat,ai,pepe,moon,elon,frog").split(",") if k.strip()],
    "MAX_POSITIONS": int(os.getenv("MAX_POSITIONS", "8")),
    "MIN_SCORE": int(os.getenv("MIN_SCORE", "4")),
    "TP_MULTIPLIER": float(os.getenv("TP_MULTIPLIER", "2.0")),   # simulated 2x
    "SL_MULTIPLIER": float(os.getenv("SL_MULTIPLIER", "0.5")),   # simulated 0.5x
    "MAX_HOLD_MINUTES": int(os.getenv("MAX_HOLD_MINUTES", "30")),
    "STATE_FILE": "state.json",
    "LOG_FILE": "trades.log",
}
# ==================================================

API_KEY = os.getenv("PUMPPORTAL_API_KEY", "")
STATE_PATH = Path(CONFIG["STATE_FILE"])

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(CONFIG["LOG_FILE"]), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

positions: Dict[str, Dict[str, Any]] = {}
seen = set()
stats = {"buys": 0, "sells": 0, "wins": 0, "losses": 0}

def load_state():
    global positions, stats
    if STATE_PATH.exists():
        try:
            data = json.loads(STATE_PATH.read_text())
            positions = data.get("positions", {})
            stats = data.get("stats", stats)
            logger.info(f"Loaded {len(positions)} positions from state")
        except Exception as e:
            logger.warning(f"Could not load state: {e}")

def save_state():
    try:
        STATE_PATH.write_text(json.dumps({"positions": positions, "stats": stats, "updated": datetime.utcnow().isoformat()}, indent=2))
    except Exception as e:
        logger.error(f"Save state failed: {e}")

def score_token(name: str, symbol: str) -> int:
    text = f"{name} {symbol}".lower()
    score = 0
    for kw in CONFIG["KEYWORDS"]:
        if kw.lower() in text:
            score += 3
    if 3 <= len(symbol) <= 6:
        score += 2
    if symbol.isupper():
        score += 1
    if any(word in text for word in ["ai", "agent", "bot", "moon", "pump"]):
        score += 1
    return min(score, 12)

def log_trade(action: str, mint: str, details: str):
    logger.info(f"{action} | {mint[:8]}... | {details}")

async def paper_buy(mint: str, name: str, symbol: str, score: int):
    if len(positions) >= CONFIG["MAX_POSITIONS"] or mint in positions:
        return
    positions[mint] = {
        "name": name,
        "symbol": symbol,
        "sol": CONFIG["BUY_AMOUNT_SOL"],
        "score": score,
        "entry": time.time(),
        "entry_iso": datetime.utcnow().isoformat(),
        "status": "open",
    }
    stats["buys"] += 1
    log_trade("PAPER_BUY", mint, f"{symbol} score={score} {CONFIG['BUY_AMOUNT_SOL']} SOL")
    save_state()

async def paper_sell(mint: str, reason: str = "manual"):
    if mint not in positions:
        return
    pos = positions.pop(mint)
    held_min = (time.time() - pos["entry"]) / 60
    # Simulate outcome based on hold time + score (purely educational)
    outcome = "win" if pos["score"] >= 6 and held_min < 20 else "loss"
    if outcome == "win":
        stats["wins"] += 1
    else:
        stats["losses"] += 1
    stats["sells"] += 1
    log_trade("PAPER_SELL", mint, f"{pos['symbol']} {reason} held={held_min:.1f}m outcome={outcome}")
    save_state()

def real_buy(mint: str):
    if not API_KEY:
        logger.error("No API key")
        return
    try:
        r = requests.post(
            f"https://pumpportal.fun/api/trade?api-key={API_KEY}",
            json={
                "action": "buy",
                "mint": mint,
                "amount": CONFIG["BUY_AMOUNT_SOL"],
                "denominatedInSol": "true",
                "slippage": CONFIG["SLIPPAGE"],
                "priorityFee": CONFIG["PRIORITY_FEE"],
                "pool": "auto",
            },
            timeout=30,
        )
        log_trade("REAL_BUY", mint, str(r.json()))
    except Exception as e:
        logger.error(f"Real buy failed: {e}")

async def manage_positions():
    """Background loop: auto-exit on time or simulated TP/SL."""
    while True:
        await asyncio.sleep(30)
        now = time.time()
        to_close = []
        for mint, pos in list(positions.items()):
            held_min = (now - pos["entry"]) / 60
            if held_min >= CONFIG["MAX_HOLD_MINUTES"]:
                to_close.append((mint, "max_hold"))
            # Simple simulated TP/SL trigger (random-ish based on score)
            elif pos["score"] >= 7 and held_min > 5 and (now % 17 < 2):
                to_close.append((mint, "simulated_tp"))
            elif pos["score"] < 4 and held_min > 8:
                to_close.append((mint, "simulated_sl"))
        for mint, reason in to_close:
            await paper_sell(mint, reason)

async def handle(msg: dict):
    mint = msg.get("mint")
    name = msg.get("name", "")
    symbol = msg.get("symbol", "")
    if not mint or mint in seen:
        return
    seen.add(mint)
    score = score_token(name, symbol)
    logger.info(f"NEW {symbol} ({name}) score={score} | {mint}")

    if score >= CONFIG["MIN_SCORE"]:
        if CONFIG["PAPER_TRADING"]:
            await paper_buy(mint, name, symbol, score)
        else:
            real_buy(mint)

async def ws_loop():
    uri = "wss://pumpportal.fun/api/data"
    while True:
        try:
            async with websockets.connect(uri) as ws:
                logger.info("Connected to PumpPortal")
                await ws.send(json.dumps({"method": "subscribeNewToken"}))
                async for raw in ws:
                    try:
                        await handle(json.loads(raw))
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"WS error: {e}. Reconnecting...")
            await asyncio.sleep(5)

def show_positions():
    print("\n=== OPEN POSITIONS ===")
    if not positions:
        print("(none)")
    else:
        for m, p in positions.items():
            held = (time.time() - p["entry"]) / 60
            print(f"{p['symbol']:8} score={p['score']} held={held:.1f}m  {m[:12]}...")
    print(f"Stats: buys={stats['buys']} sells={stats['sells']} wins={stats['wins']} losses={stats['losses']}")
    print("=======================\n")

async def main():
    load_state()
    print("Pump.fun AI World started")
    print(f"Mode: {'PAPER' if CONFIG['PAPER_TRADING'] else 'REAL'} | min score {CONFIG['MIN_SCORE']} | max pos {CONFIG['MAX_POSITIONS']}")
    print("Commands: p (positions) | s <mint> (sell) | stats | q (quit)\n")

    asyncio.create_task(ws_loop())
    asyncio.create_task(manage_positions())
    loop = asyncio.get_event_loop()

    while True:
        try:
            cmd = await loop.run_in_executor(None, input, "> ")
            cmd = cmd.strip().lower()
            if cmd in ("q", "quit"):
                break
            if cmd in ("p", "positions"):
                show_positions()
            elif cmd == "stats":
                print(stats)
            elif cmd.startswith("s "):
                await paper_sell(cmd.split()[1], "manual")
            else:
                print("Unknown. p / s <mint> / stats / q")
        except (EOFError, KeyboardInterrupt):
            break

    save_state()
    logger.info("Stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        save_state()
        print("\nStopped.")
