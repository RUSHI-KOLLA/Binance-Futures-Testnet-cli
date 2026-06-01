# Binance Futures Testnet Trading Bot (USDT-M)

A clean, structured Python CLI application to place orders on the **Binance Futures Testnet / Demo Trading** (`https://demo-fapi.binance.com`).

### 🎥 [Watch the Live Demo Video Here](./demo.mp4)

---

## Features

| Feature | Details |
|---|---|
| **Order types** | `MARKET`, `LIMIT`, `STOP_MARKET`, `STOP_LIMIT` (bonus) |
| **Sides** | `BUY` / `SELL` |
| **CLI modes** | Direct (argparse) **and** interactive wizard (questionary) — bonus |
| **Dry-run** | Simulate any order locally with `--dry-run` |
| **Logging** | Structured file logging (no ANSI codes); console logging for humans |
| **Security** | Signatures masked in logs; `.env` excluded via `.gitignore` |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py           # Binance REST client — HMAC-SHA256 signing, time sync
│   ├── orders.py           # Order orchestrator — validate → summarise → execute → display
│   ├── validators.py       # Input validation rules
│   └── logging_config.py   # File + console logging with ANSI-strip filter
├── logs/
│   ├── trading_bot.log     # Combined audit trail
│   ├── market_order.log    # Extracted MARKET order log
│   └── limit_order.log     # Extracted LIMIT order log
├── cli.py                  # Entry point (direct + interactive)
├── requirements.txt
├── .env.example            # Credential template
├── .gitignore
└── README.md
```

---

## Setup

### 1. Prerequisites

- Python 3.10+
- A Binance Futures Testnet/Demo Trading account — register API keys at <https://demo.binance.com/en/my/settings/api-management>

### 2. Install

```bash
cd trading_bot

# Create & activate virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure credentials

```bash
cp .env.example .env
# Edit .env and paste your Testnet API key + secret
```

---

## Usage

> Activate the virtual environment first: `source .venv/bin/activate`

### Interactive mode (run with no arguments)

```bash
python cli.py
# or explicitly:
python cli.py -i
```

You will be guided through symbol, side, order type, quantity, price, and dry-run selection via an interactive menu.

### Direct CLI mode

#### Market order (dry-run)

```bash
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.05 \
  --dry-run
```

#### Limit order (live testnet)

```bash
python cli.py \
  --symbol BTCUSDT \
  --side SELL \
  --type LIMIT \
  --quantity 0.02 \
  --price 65000
```

#### Stop-Limit order (live testnet)

```bash
python cli.py \
  --symbol BTCUSDT \
  --side SELL \
  --type STOP_LIMIT \
  --quantity 0.02 \
  --price 63900 \
  --stop-price 64000
```

#### Stop-Market order (dry-run)

```bash
python cli.py \
  --symbol ETHUSDT \
  --side BUY \
  --type STOP_MARKET \
  --quantity 1.0 \
  --stop-price 3500 \
  --dry-run
```

### All CLI flags

| Flag | Short | Required | Description |
|---|---|---|---|
| `--symbol` | `-s` | Yes* | Trading pair, e.g. `BTCUSDT` |
| `--side` | `-d` | Yes* | `BUY` or `SELL` |
| `--type` | `-t` | Yes* | `MARKET`, `LIMIT`, `STOP_MARKET`, `STOP_LIMIT` |
| `--quantity` | `-q` | Yes* | Amount to trade |
| `--price` | `-p` | For LIMIT/STOP_LIMIT | Limit price in USDT |
| `--stop-price` | — | For STOP_MARKET/STOP_LIMIT | Trigger price in USDT |
| `--dry-run` | — | No | Simulate locally without API call |
| `--interactive` | `-i` | No | Force interactive wizard |

\* Required in direct mode. In interactive mode, inputs are collected via prompts.

---

## Sample Output

```
═══════════════ VALIDATING INPUTS ═══════════════
✓ All inputs validated successfully.

═══════════════ ORDER REQUEST SUMMARY ═══════════════
  Symbol            BTCUSDT
  Side              BUY
  Order Type        MARKET
  Quantity          0.05
  Mode              DRY-RUN (simulated)
════════════════════════════════════════════════

Placing MARKET BUY order for 0.05 BTCUSDT …
[DRY-RUN] Simulating MARKET BUY order for 0.05 BTCUSDT

═══════════════ ORDER RESPONSE DETAILS ═══════════════
  Order ID          234911674
  Status            FILLED
  Executed Qty      0.05
  Avg / Limit Price 50000.00 USDT
════════════════════════════════════════════════

✔ SUCCESS — Order placed (ID: 234911674)
```

---

## Architecture & Design Decisions

1. **Direct REST over `python-binance`** — We use raw `requests` calls with manual HMAC-SHA256 signing instead of the `python-binance` SDK. This avoids version-pinning issues and makes every API interaction transparent and auditable.

2. **Server time synchronisation** — Before each signed request, the client fetches `/fapi/v1/time` from the exchange and uses that timestamp in the signature. This prevents the common "Timestamp … ahead of the server's time" rejection. Falls back to local clock on failure.

3. **Layered architecture** — `client.py` (API transport) → `orders.py` (business logic / orchestration) → `cli.py` (user interface). Each layer has a single responsibility and can be tested or replaced independently.

4. **ANSI-stripped file logs** — A custom logging filter removes terminal colour codes before writing to the log file, keeping logs machine-readable while the console stays colourful.

5. **Signature masking** — The `signature` field is replaced with `***` in all debug logs to prevent accidental credential exposure.

6. **Dry-run mode** — Returns realistic mock responses matching the Binance Futures API schema, allowing full end-to-end testing without API credentials.

---

## Assumptions

- The application targets **Binance Futures Testnet / Demo Trading** only (`https://demo-fapi.binance.com`). It should not be used with mainnet credentials.
- Quantity precision and minimum notional checks are not enforced client-side; the exchange will reject invalid values with descriptive error codes.
- The log files included in `logs/` contain real transactions successfully executed on the testnet.

---

## Log Files

| File | Contents |
|---|---|
| `logs/trading_bot.log` | Full audit trail — all orders, errors, API responses |
| `logs/market_order.log` | Extracted log for one MARKET BUY order |
| `logs/limit_order.log` | Extracted log for one LIMIT SELL order |
