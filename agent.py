#!/usr/bin/env python3
"""
Pump.fun AI World — paper-trading agent by default.
Streams new tokens, scores them, and simulates trades.
HIGH RISK. Most tokens go to zero.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
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
    "PAPER_TRADING": True,
    "BUY_AMOUNT_SOL": 0.01,
    "SLIPPAGE": 15,
    "PRIORITY_FEE": 0.00005,
    "KEYWORDS": ["dog", "cat", "ai", "pepe", "moon", "elon"],  # empty list = all tokens
    "MAX_POSITIONS": 5,
    "MIN_SCORE": 3,  # simple score threshold
    "LOG_FILE": "trades.log",
}
# ==================================================

API_KEY = os.getenv("PUMPPORTAL_API_KEY", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(CONFIG["LOG_FILE"]), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

positions: Dict[str, Dict[str, Any]] = {}
seen = set()

def score_token(name: str, symbol: str) -> int:
    """Simple AI-style scoring. Extend with real LLM later."""
    text = f"{name} {symbol}".lower()
    score = 0
    for kw in CONFIG["KEYWORDS"]:
        if kw.lower() in text:
            score += 2
    if len(symbol) <= 6:
        score += 1
    if any(c.isupper() for c in symbol):
        score += 1
    return score

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
        "time": datetime.utcnow().isoformat(),
    }
    log_trade("PAPER_BUY", mint, f"{symbol} score={score} {CONFIG['BUY_AMOUNT_SOL']} SOL")

async def paper_sell(mint: str):
    if mint in positions:
        pos = positions.pop(mint)
        log_trade("PAPER_SELL", mint, f"{pos['symbol']} closed")

def real_buy(mint: str):
    if not API_KEY:
        logger.error("No API key for real trade")
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
    print("\n=== POSITIONS ===")
    if not positions:
        print("(none)")
    for m, p in positions.items():
        print(f"{p['symbol']:8} score={p['score']} {p['sol']} SOL  {m[:12]}...")
    print("=================\n")

async def main():
    print("Pump.fun AI World started")
    print(f"Mode: {'PAPER' if CONFIG['PAPER_TRADING'] else 'REAL'} | min score {CONFIG['MIN_SCORE']}")
    print("Commands: p (positions) | s <mint> (sell) | q (quit)\n")

    task = asyncio.create_task(ws_loop())
    loop = asyncio.get_event_loop()

    while True:
        try:
            cmd = await loop.run_in_executor(None, input, "> ")
            cmd = cmd.strip().lower()
            if cmd in ("q", "quit"):
                break
            if cmd in ("p", "positions"):
                show_positions()
            elif cmd.startswith("s "):
                await paper_sell(cmd.split()[1])
            else:
                print("Unknown. p / s <mint> / q")
        except (EOFError, KeyboardInterrupt):
            break

    task.cancel()
    logger.info("Stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
