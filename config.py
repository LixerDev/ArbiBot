import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

    SCAN_AMOUNT_USD: float = float(os.getenv("SCAN_AMOUNT_USD", "1000"))
    MIN_PROFIT_USD: float = float(os.getenv("MIN_PROFIT_USD", "0.50"))
    MIN_SPREAD_PCT: float = float(os.getenv("MIN_SPREAD_PCT", "0.0"))
    REFRESH_INTERVAL: int = int(os.getenv("REFRESH_INTERVAL", "5"))
    PROFITABLE_ONLY: bool = os.getenv("PROFITABLE_ONLY", "false").lower() == "true"

    RAYDIUM_AMM_FEE_BPS: int = int(os.getenv("RAYDIUM_AMM_FEE_BPS", "25"))
    RAYDIUM_CLMM_FEE_BPS: int = int(os.getenv("RAYDIUM_CLMM_FEE_BPS", "4"))
    ORCA_FEE_BPS: int = int(os.getenv("ORCA_FEE_BPS", "30"))
    GAS_COST_USD: float = float(os.getenv("GAS_COST_USD", "0.001"))
    TXS_PER_ARB: int = int(os.getenv("TXS_PER_ARB", "2"))

    ALERT_COOLDOWN_MINUTES: int = int(os.getenv("ALERT_COOLDOWN_MINUTES", "5"))

    WATCH_PAIRS_RAW: str = os.getenv(
        "WATCH_PAIRS",
        "SOL/USDC,JUP/USDC,BONK/USDC,WIF/USDC,mSOL/USDC,PYTH/USDC,JTO/USDC"
    )

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Jupiter Quote API
    JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"

    @property
    def default_pairs(self) -> list[tuple[str, str]]:
        pairs = []
        for pair_str in self.WATCH_PAIRS_RAW.split(","):
            pair_str = pair_str.strip()
            if "/" in pair_str:
                base, quote = pair_str.split("/", 1)
                pairs.append((base.strip(), quote.strip()))
        return pairs

config = Config()
