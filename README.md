# ⚡ ArbiBot

Real-time cross-DEX arbitrage detector for Solana. Compares live quotes from **Raydium**, **Orca**, and **Jupiter**, calculates net profit after swap fees and gas, and alerts you on Discord when a genuinely profitable opportunity is found.

**Built by LixerDev**

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![Solana](https://img.shields.io/badge/network-Solana-9945FF)
![License](https://img.shields.io/badge/license-MIT-purple)

---

## ⚠️ Important: Detection vs Execution

> ArbiBot **detects** and **calculates** arbitrage opportunities. It does **not** execute trades. Executing on-chain arbitrage requires fast transaction submission (ideally via Jito bundles), which is outside the scope of this tool.

---

## 🔍 How It Works

```
Step 1: Fetch live quotes from Raydium, Orca, and Jupiter for each token pair
Step 2: Compare effective prices across DEXes
Step 3: Identify the best buy DEX and best sell DEX
Step 4: Calculate gross profit (price spread × amount)
Step 5: Deduct swap fees (0.25% Raydium, 0.30% Orca) + gas (~$0.001/tx)
Step 6: If net profit > threshold → alert!
```

### Example Opportunity

```
┌─────────────────────────────────────────────────────────────┐
│  ⚡ ARBITRAGE OPPORTUNITY FOUND                              │
│                                                              │
│  Pair:         SOL → USDC → SOL (triangular)                │
│  Amount:       10 SOL  ($1,620)                             │
│                                                              │
│  Buy on:       Orca      →  $161.84 / SOL                   │
│  Sell on:      Raydium   →  $162.31 / SOL                   │
│  Spread:       $0.47 / SOL  (+0.29%)                        │
│                                                              │
│  Gross Profit: $4.70                                        │
│  Swap Fees:   -$2.43  (Orca 0.30% + Raydium 0.25%)         │
│  Gas Fees:    -$0.002                                       │
│  ─────────────────────────────────────────────────          │
│  Net Profit:  +$2.26  (0.14%)  ✅ PROFITABLE                │
│                                                              │
│  Execute:  Buy 10 SOL on Orca → Sell on Raydium             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/LixerDev/ArbiBot.git
cd ArbiBot
pip install -r requirements.txt
cp .env.example .env
# Optional: add Discord webhook for alerts

# Watch all default token pairs in real time
python main.py watch

# Scan once and show all spreads
python main.py scan

# Simulate specific pair and amount
python main.py simulate --pair SOL/USDC --amount 10

# Watch custom pairs
python main.py watch --pairs SOL/USDC WIF/USDC BONK/USDC

# Only alert on profitable opportunities (no noise)
python main.py watch --profitable-only
```

---

## 📊 Dashboard Preview

```
⚡ ArbiBot — Live Scanner  |  7 pairs  |  refresh: 5s  |  09:22:41 UTC

  Pair         Raydium      Orca         Jupiter     Spread   Net Profit
  SOL/USDC    $162.31      $161.84      $162.28     +0.29%   +$2.26 ✅
  JUP/USDC    $0.8241      $0.8239      $0.8243     +0.02%   -$0.12 ❌
  BONK/USDC   $0.00002134  $0.00002137  $0.00002135 +0.14%   -$0.05 ❌
  WIF/USDC    $2.1840      $2.1867      $2.1852     +0.12%   +$0.08 ✅
  mSOL/USDC   $181.20      $181.18      $181.22     +0.02%   -$0.31 ❌
  ETH/USDC    $3,420.11    $3,419.87    $3,420.34   +0.01%   -$1.22 ❌
  PYTH/USDC   $0.4120      $0.4118      $0.4121     +0.07%   +$0.03 ✅

  Last scan: 0.8s  |  Opportunities found: 2  |  Discord alerts: ENABLED
```

---

## 🧮 Fee Model

ArbiBot uses accurate real-world fee data:

| DEX | Swap Fee | Notes |
|---|---|---|
| Raydium AMM | 0.25% | Standard AMM pools |
| Raydium CLMM | 0.04% | Concentrated liquidity |
| Orca Whirlpool | 0.30% | Standard pools |
| Orca Concentrated | 0.05% | Whirlpool CLMM |
| Jupiter | Best route | Aggregated, includes underlying DEX fees |
| Network fee | ~$0.001 | Per transaction, estimated |

---

## ⚙️ Configuration

| Variable | Description | Default |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | Discord webhook for alerts | Optional |
| `MIN_PROFIT_USD` | Min net profit to alert (USD) | 0.50 |
| `SCAN_AMOUNT_USD` | Quote size in USD | 1000 |
| `REFRESH_INTERVAL` | Seconds between scans | 5 |
| `RAYDIUM_FEE_BPS` | Raydium AMM fee in bps | 25 |
| `ORCA_FEE_BPS` | Orca fee in bps | 30 |
| `GAS_COST_USD` | Estimated gas per transaction | 0.001 |

---

## 🏗️ Architecture

```
main.py (Typer CLI)
    ├── watch → Scanner loop (every N seconds)
    └── scan / simulate → One-shot
            │
            └── Scanner
                    ├── QuoteFetcher   → Jupiter API (per-DEX routing)
                    ├── ArbDetector    → Find best buy/sell DEX per pair
                    ├── ProfitCalc     → Gross spread - fees - gas = net profit
                    ├── Alerter        → Discord webhook + cooldown
                    └── Dashboard      → Rich live terminal display
```
