# Binance Futures Testnet Trading Bot

A clean, modular Python CLI application for placing orders on the **Binance Futures Testnet (USDT-M)**.

Supports **Market**, **Limit**, and **Stop-Market** orders with structured logging, robust input validation, and clear terminal output.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # Binance REST client (auth, signing, HTTP)
│   ├── orders.py            # Order placement logic & result types
│   ├── validators.py        # Input validation (raises on bad data)
│   └── logging_config.py   # Rotating file + console log setup
├── cli.py                   # CLI entry point (argparse)
├── logs/
│   └── trading_bot.log      # Auto-created on first run
├── README.md
└── requirements.txt
```

### Layer responsibilities

| Layer | File | Responsibility |
|---|---|---|
| Client | `bot/client.py` | HMAC signing, HTTP, error parsing |
| Orders | `bot/orders.py` | Param building, API call, result mapping |
| Validators | `bot/validators.py` | Strict input validation before any API call |
| CLI | `cli.py` | Argument parsing, user output, exit codes |

---

## Setup

### 1. Prerequisites

- Python 3.9+
- A [Binance Futures Testnet](https://testnet.binancefuture.com) account

### 2. Generate Testnet API Credentials

1. Visit https://testnet.binancefuture.com
2. Log in (GitHub OAuth or email)
3. Go to **API Key** section → click **Generate**
4. Copy your **API Key** and **Secret Key** — the secret is shown only once

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Only `requests` is required — no heavy SDK.

### 4. Supply Credentials

**Option A — Environment variables (recommended):**

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
```

**Option B — CLI flags:**

```bash
python cli.py --api-key YOUR_KEY --api-secret YOUR_SECRET ...
```

---

## How to Run

### Market Order — BUY

```bash
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001
```

### Limit Order — SELL

```bash
python cli.py \
  --symbol BTCUSDT \
  --side SELL \
  --type LIMIT \
  --quantity 0.001 \
  --price 100000
```

### Stop-Market Order — SELL (bonus order type)

```bash
python cli.py \
  --symbol BTCUSDT \
  --side SELL \
  --type STOP_MARKET \
  --quantity 0.001 \
  --price 95000
```

For Stop-Market orders `--price` is interpreted as the **stop trigger price**.

### Debug Logging

```bash
python cli.py --log-level DEBUG --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

---

## Example Terminal Output

```
  ____  _                               ____        _
 | __ )(_)_ __   __ _ _ __   ___ ___  | __ )  ___ | |_
 ...

───────────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
───────────────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001
───────────────────────────────────────────────────────

  Submitting order…

───────────────────────────────────────────────────────
  ORDER RESPONSE
───────────────────────────────────────────────────────
  ✓  Order placed successfully
     Order ID      : 4030880884
     Client ID     : x-xcKtGieH4a30e3d10df7a2ed0c0b3d
     Symbol        : BTCUSDT
     Side          : BUY
     Type          : MARKET
     Status        : FILLED
     Orig Qty      : 0.001
     Executed Qty  : 0.001
     Avg Price     : 97345.20000
───────────────────────────────────────────────────────
```

---

## Log File

All API requests, responses, and errors are written to `logs/trading_bot.log` (rotating, max 5 × 5 MB).

Sample entries:

```
2025-06-10 14:22:03 | INFO     | trading_bot.orders | Placing BUY MARKET order | symbol=BTCUSDT qty=0.001 price=N/A
2025-06-10 14:22:03 | INFO     | trading_bot.orders | Order accepted | id=4030880884 status=FILLED executedQty=0.001
2025-06-10 14:29:03 | ERROR    | trading_bot.client | Binance API error code=-1111 msg=Parameter 'quantity' has too many decimal places.
```

API signatures are **always redacted** (`***`) in logs.

---

## Validation & Error Handling

| Error case | Behaviour |
|---|---|
| Missing `--price` for LIMIT order | `ValidationError` before any API call |
| Non-numeric quantity / price | `ValidationError` before any API call |
| Negative or zero quantity | `ValidationError` before any API call |
| Invalid symbol characters | `ValidationError` before any API call |
| Binance API error (e.g. `-1111`) | `BinanceAPIError` caught, clean failure message printed |
| Network timeout / DNS failure | `requests.RequestException` caught, logged, clean failure |

Exit codes: `0` = success, `1` = validation failure, `2` = API/network failure.

---

## Assumptions

- The testnet base URL is `https://testnet.binancefuture.com` (configurable via `--base-url`).
- All orders use **one-way position mode** (`positionSide=BOTH` is the default).
- LIMIT orders use **GTC** (Good-Till-Cancelled) time-in-force.
- Quantity and price precision must comply with the symbol's exchange filters — the bot passes values as-is; Binance will reject invalid precision with error `-1111`.
- No position or balance checks are performed before order submission.

---

## Bonus Feature

**Stop-Market orders** are fully supported as a third order type (`--type STOP_MARKET`). Pass `--price` as the stop-trigger price.
