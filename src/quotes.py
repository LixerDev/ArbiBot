"""
QuoteFetcher — fetches live price quotes from Raydium, Orca, and Jupiter.

Uses Jupiter's Quote API v6 with DEX-specific routing filters.
Jupiter allows restricting quotes to specific AMMs:
  - dexes=Raydium        → only Raydium AMM/CLMM pools
  - dexes=Orca           → only Orca Whirlpool pools
  - (no filter)          → Jupiter best route across all DEXes

This lets us compare effective prices across platforms in real time.
"""

import aiohttp
import asyncio
from src.models import Quote, TokenPair, DEX, TOKEN_DECIMALS
from src.logger import get_logger
from config import config

logger = get_logger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=8)

# DEX filter strings for Jupiter API
DEX_FILTERS = {
    DEX.RAYDIUM: "Raydium",
    DEX.ORCA:    "Orca",
    DEX.JUPITER: None,  # No filter = best route
}

# Fee rates per DEX (basis points)
DEX_FEES_BPS = {
    DEX.RAYDIUM: config.RAYDIUM_AMM_FEE_BPS,
    DEX.ORCA:    config.ORCA_FEE_BPS,
    DEX.JUPITER: 0,  # Jupiter fee is already included in the quote
}


class QuoteFetcher:
    def __init__(self):
        self.api_url = config.JUPITER_QUOTE_API

    async def _fetch_quote(
        self,
        pair: TokenPair,
        in_amount_raw: int,
        dex: DEX,
    ) -> Quote | None:
        """
        Fetch a single quote from Jupiter API with optional DEX filter.

        Parameters:
        - pair: Token pair (base/quote)
        - in_amount_raw: Input amount in raw units (considering decimals)
        - dex: Which DEX to route through (or Jupiter best)

        Returns:
        - Quote or None if fetch fails
        """
        params = {
            "inputMint": pair.base_mint,
            "outputMint": pair.quote_mint,
            "amount": str(in_amount_raw),
            "slippageBps": "50",
            "onlyDirectRoutes": "true",
            "restrictIntermediateTokens": "true",
        }

        dex_filter = DEX_FILTERS.get(dex)
        if dex_filter:
            params["dexes"] = dex_filter

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    params=params,
                    timeout=TIMEOUT
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()

            if not data or "outAmount" not in data:
                return None

            in_decimals = pair.base_decimals
            out_decimals = pair.quote_decimals

            in_amt = int(data["inAmount"]) / (10 ** in_decimals)
            out_amt = int(data["outAmount"]) / (10 ** out_decimals)
            price_impact = float(data.get("priceImpactPct", 0)) * 100

            if in_amt == 0:
                return None

            effective_price = out_amt / in_amt

            # Determine route label
            route_plan = data.get("routePlan", [])
            route_label = " → ".join([
                step.get("swapInfo", {}).get("label", "?")
                for step in route_plan[:3]
            ]) or dex.value

            fee_pct = DEX_FEES_BPS.get(dex, 0) / 100.0

            return Quote(
                dex=dex,
                pair=pair,
                in_amount=in_amt,
                out_amount=out_amt,
                effective_price=effective_price,
                price_impact_pct=price_impact,
                fee_pct=fee_pct,
                route_label=route_label,
                raw=data,
            )

        except asyncio.TimeoutError:
            logger.debug(f"Timeout fetching {dex.value} quote for {pair.display}")
            return None
        except Exception as e:
            logger.debug(f"Quote fetch error ({dex.value}, {pair.display}): {e}")
            return None

    async def fetch_all_quotes(
        self,
        pair: TokenPair,
        amount_usd: float,
        base_price_usd: float = 1.0,
    ) -> list[Quote]:
        """
        Fetch quotes from all DEXes concurrently for a token pair.

        Parameters:
        - pair: Token pair
        - amount_usd: Trade size in USD
        - base_price_usd: Current price of base token (to compute raw amount)

        Returns:
        - list[Quote]: All valid quotes, sorted by effective price descending
        """
        if not pair.base_mint or not pair.quote_mint:
            logger.warning(f"Unknown token in pair: {pair.display}")
            return []

        # Calculate raw input amount
        in_decimals = pair.base_decimals
        amount_base = amount_usd / max(base_price_usd, 0.0001)
        in_amount_raw = int(amount_base * (10 ** in_decimals))

        if in_amount_raw <= 0:
            return []

        # Fetch all DEX quotes concurrently
        tasks = [
            self._fetch_quote(pair, in_amount_raw, DEX.RAYDIUM),
            self._fetch_quote(pair, in_amount_raw, DEX.ORCA),
            self._fetch_quote(pair, in_amount_raw, DEX.JUPITER),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        quotes = []
        for result in results:
            if isinstance(result, Quote) and result.is_valid:
                quotes.append(result)

        return sorted(quotes, key=lambda q: q.effective_price, reverse=True)

    async def get_base_price(self, pair: TokenPair) -> float:
        """
        Get approximate current price of base token in USD.
        Uses Jupiter best route for accuracy.
        """
        # For stablecoins, price is always 1
        stable_mints = {
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",   # USDT
        }
        if pair.base_mint in stable_mints:
            return 1.0

        # Small quote to get price
        in_decimals = pair.base_decimals
        small_amount = int(0.01 * (10 ** in_decimals))  # 0.01 base token

        quote = await self._fetch_quote(pair, small_amount, DEX.JUPITER)
        if quote and quote.is_valid:
            return quote.effective_price
        return 1.0
