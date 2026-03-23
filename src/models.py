from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class DEX(str, Enum):
    RAYDIUM    = "Raydium"
    ORCA       = "Orca"
    JUPITER    = "Jupiter"
    RAYDIUM_CLMM = "Raydium CLMM"
    ORCA_CLMM  = "Orca (Whirlpool)"
    UNKNOWN    = "Unknown"


DEX_COLORS = {
    DEX.RAYDIUM:      "blue",
    DEX.ORCA:         "cyan",
    DEX.JUPITER:      "green",
    DEX.RAYDIUM_CLMM: "blue",
    DEX.ORCA_CLMM:    "cyan",
    DEX.UNKNOWN:      "dim",
}

# Known Solana token mints
TOKEN_MINTS = {
    "SOL":   "So11111111111111111111111111111111111111112",
    "USDC":  "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT":  "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "mSOL":  "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
    "stSOL": "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",
    "JUP":   "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "JTO":   "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
    "WIF":   "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "BONK":  "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "PYTH":  "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
    "RNDR":  "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",
    "RAY":   "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "ORCA":  "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
}

TOKEN_DECIMALS = {
    "So11111111111111111111111111111111111111112": 9,   # SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 6, # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": 6,  # USDT
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So": 9,  # mSOL
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": 6,  # JUP
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL": 9,  # JTO
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm": 6, # WIF
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": 5, # BONK
    "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3": 6, # PYTH
}


@dataclass
class TokenPair:
    base_symbol: str
    quote_symbol: str

    @property
    def base_mint(self) -> str:
        return TOKEN_MINTS.get(self.base_symbol, "")

    @property
    def quote_mint(self) -> str:
        return TOKEN_MINTS.get(self.quote_symbol, "")

    @property
    def base_decimals(self) -> int:
        return TOKEN_DECIMALS.get(self.base_mint, 6)

    @property
    def quote_decimals(self) -> int:
        return TOKEN_DECIMALS.get(self.quote_mint, 6)

    @property
    def display(self) -> str:
        return f"{self.base_symbol}/{self.quote_symbol}"


@dataclass
class Quote:
    """A price quote from a specific DEX for a token pair."""
    dex: DEX
    pair: TokenPair
    in_amount: float               # Input amount (base token)
    out_amount: float              # Output amount (quote token)
    effective_price: float         # out_amount / in_amount
    price_impact_pct: float        # Slippage/price impact
    fee_pct: float                 # Swap fee percentage
    route_label: str               # DEX route description
    raw: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def is_valid(self) -> bool:
        return self.effective_price > 0 and self.out_amount > 0


@dataclass
class ArbitrageOpportunity:
    """A detected arbitrage opportunity between two DEXes."""
    pair: TokenPair
    amount_base: float             # How much base token to buy/sell
    amount_usd: float              # USD value of the trade

    buy_dex: DEX                   # Cheaper DEX (buy here)
    sell_dex: DEX                  # More expensive DEX (sell here)
    buy_price: float               # Price on buy DEX
    sell_price: float              # Price on sell DEX

    gross_spread_usd: float        # Gross profit before fees
    spread_pct: float              # Spread as percentage

    buy_fee_usd: float             # Fee on buy DEX
    sell_fee_usd: float            # Fee on sell DEX
    gas_fee_usd: float             # Network gas for both txs

    net_profit_usd: float          # Final profit after all fees
    profitable: bool               # True if net_profit > threshold

    all_quotes: list[Quote] = field(default_factory=list)
    detected_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "pair": self.pair.display,
            "amount_usd": round(self.amount_usd, 2),
            "buy_dex": self.buy_dex.value,
            "sell_dex": self.sell_dex.value,
            "buy_price": round(self.buy_price, 8),
            "sell_price": round(self.sell_price, 8),
            "spread_pct": round(self.spread_pct, 4),
            "gross_profit_usd": round(self.gross_spread_usd, 4),
            "fees_usd": round(self.buy_fee_usd + self.sell_fee_usd + self.gas_fee_usd, 4),
            "net_profit_usd": round(self.net_profit_usd, 4),
            "profitable": self.profitable,
        }


@dataclass
class ScanResult:
    """Results from a single scan cycle."""
    pairs_scanned: int = 0
    opportunities: list[ArbitrageOpportunity] = field(default_factory=list)
    profitable_count: int = 0
    scan_duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def best_opportunity(self) -> Optional[ArbitrageOpportunity]:
        profitable = [o for o in self.opportunities if o.profitable]
        if not profitable:
            return None
        return max(profitable, key=lambda o: o.net_profit_usd)

from typing import Optional
