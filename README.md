# Pump.fun AI World

**⚠️ HIGH RISK — EDUCATIONAL USE ONLY**

Most Pump.fun tokens go to zero. Automated trading can lose all funds quickly. This is not financial advice. Start in paper mode. Never commit private keys.

## What this is

An AI-powered agent that:
- Streams live new token launches from PumpPortal WebSocket
- Scores tokens with rule-based + optional LLM-style logic (narrative, keywords, freshness)
- Paper trades by default (simulated positions)
- Can optionally execute real trades via PumpPortal Lightning API (requires your API key)
- Logs decisions and open positions
- Includes a simple live dashboard

## Quick start

```bash
git clone https://github.com/unknownuser1942/pumpfun-ai-world.git
cd pumpfun-ai-world
pip install -r requirements.txt
cp .env.example .env   # edit if you want real trading later
python agent.py
```

Open `dashboard.html` in a browser for a live feed view.

## Configuration

Edit the `CONFIG` dict at the top of `agent.py`:

- `PAPER_TRADING = True` (strongly recommended)
- `BUY_AMOUNT_SOL`
- `KEYWORDS` filter
- `MAX_POSITIONS`
- `MIN_SCORE` threshold for AI-style scoring

## Real trading (optional, high risk)

1. Get a PumpPortal API key from https://pumpportal.fun
2. Link a funded Solana wallet there
3. Set `PAPER_TRADING = False` and put the key in `.env` as `PUMPPORTAL_API_KEY`
4. Start with tiny amounts (0.01 SOL or less)

Private keys never enter this repo or the agent.

## Running continuously

- Local: `tmux` or `screen` + `python agent.py`
- VPS / Railway / Render / Fly.io: deploy the Python process
- GitHub Actions is not ideal for 24/7 bots (timeouts, no persistent state)

## Files

- `agent.py` — main AI agent loop
- `dashboard.html` — browser live feed
- `.env.example`
- `requirements.txt`

Built as a starter. Extend scoring, add take-profit/stop-loss, or plug in a real LLM API as needed.
