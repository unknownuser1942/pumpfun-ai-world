# Pump.fun AI World

**⚠️ HIGH RISK — EDUCATIONAL USE ONLY**

Most Pump.fun tokens go to zero. Automated trading can lose all funds quickly. This is not financial advice. Paper mode is the default and strongly recommended.

## What this is

An autonomous AI-style agent that:
- Streams live new token launches from PumpPortal WebSocket
- Scores tokens with multi-factor logic (keywords, length, patterns)
- Paper trades matches (simulated positions with TP/SL logic)
- Persists state to `state.json` so you can restart without losing positions
- Auto-exits on max hold time or simulated take-profit / stop-loss
- Optional real trading via PumpPortal Lightning (API key required)
- Live dashboard

## Quick start

```bash
git clone https://github.com/unknownuser1942/pumpfun-ai-world.git
cd pumpfun-ai-world
pip install -r requirements.txt
python agent.py
```

Open `dashboard.html` in a browser for the visual feed.

## Configuration (env vars or edit CONFIG)

```bash
export PAPER_TRADING=true
export BUY_AMOUNT_SOL=0.01
export KEYWORDS="dog,cat,ai,pepe,moon"
export MIN_SCORE=4
export MAX_POSITIONS=8
export MAX_HOLD_MINUTES=30
python agent.py
```

## CLI commands

- `p` or `positions` — show open paper positions + stats
- `s <mint>` — manual sell
- `stats` — win/loss counters
- `q` — quit (saves state)

## Real trading (optional, extreme risk)

1. Get a PumpPortal API key from https://pumpportal.fun
2. Link a funded Solana wallet
3. Set `PAPER_TRADING=false` and `PUMPPORTAL_API_KEY=yourkey`
4. Start with 0.01 SOL or less

Private keys never enter this repo.

## Running continuously

- Local: `tmux` or `screen`
- VPS / Railway / Render / Fly.io: run the Python process
- State is saved to `state.json` so restarts resume positions

## Files

- `agent.py` — main agent (scoring, paper trades, auto-exits, persistence)
- `dashboard.html` — browser live feed
- `.env.example`
- `requirements.txt`

Extend the `score_token` function or plug in a real LLM API for richer decisions.
