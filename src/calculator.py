"""
ProfitCalculator — computes net arbitrage profit after all fees.

The math:
  Gross Spread = (sell_price - buy_price) × amount_base
  Buy Fee      = amount_usd × buy_fee_pct / 100
  Sell Fee     = amount_usd × sell_fee_pct / 100
  Gas Fee      = GAS_COST_USD × TXS_PER_ARB
  Net Profit   = Gross Spread - Buy Fee - Sell Fee - Gas Fee
"""

from src.models import Quote, ArbitrageOpportunity, TokenPair, DEX
from src.logger import get_logger
from config import config

logger = get_logger(__name__)

# Fee rates per DEX (as percentage)
DEX_FEE_RATES = {
    DEX.RAYDIUM:      config.RAYDIUM_AMM_FEE_BPS / 10000,
    DEX.ORCA:         config.ORCA_FEE_BPS / 10000,
    DEX.JUPITER:      0.0,   # Jupiter fees are inside the quote already
    DEX.RAYDIUM_CLMM: config.RAYDIUM_CLMM_FEE_BPS / 10000,
    DEX.ORCA_CLMM:    0.0005,
    DEX.UNKNOWN:      0.003,
}


class ProfitCalculator:
    def calculate(
        self,
        pair: TokenPair,
        quotes: list[Quote],
        amount_usd: float,
    ) -> ArbitrageOpportunity | None:
        """
        Find the best buy/sell DEX pair and calculate net profit.

        Strategy:
        - Buy on the DEX with the highest output (most base tokens for our USD)
        - Sell on the DEX with the lowest output (they pay more per token)
        
        Wait — for BASE→QUOTE direction:
        - Highest out_amount = best sell price (you get the most USDC per SOL)
        - Lowest out_amount = cheapest buy price (spend less USDC per SOL)
        
        Since all quotes go BASE→QUOTE:
        - Best SELL = highest effective_price (most USDC per SOL)
        - Best BUY  = lowest effective_price (cheapest to acquire SOL)

        For arb: buy SOL cheaply on low-price DEX, sell on high-price DEX.

        Parameters:
        - pair: Token pair
        - quotes: List of quotes from all DEXes (BASE→QUOTE direction)
        - amount_usd: Trade size in USD

        Returns:
        - ArbitrageOpportunity or None if < 2 quotes
        """
        valid_quotes = [q for q in quotes if q.is_valid]
        if len(valid_quotes) < 2:
            return None

        # Sort by effective price
        sorted_quotes = sorted(valid_quotes, key=lambda q: q.effective_price)
        buy_quote = sorted_quotes[0]   # Lowest price = buy here
        sell_quote = sorted_quotes[-1]  # Highest price = sell here

        if buy_quote.dex == sell_quote.dex:
            return None

        buy_price = buy_quote.effective_price
        sell_price = sell_quote.effective_price

        if buy_price <= 0:
            return None

        spread_pct = ((sell_price - buy_price) / buy_price) * 100
        if spread_pct <= 0:
            return None

        # Amount of base token we can buy with amount_usd at buy_price
        amount_base = amount_usd / buy_price
        gross_spread_usd = (sell_price - buy_price) * amount_base

        # Fee calculations
        buy_fee_rate = DEX_FEE_RATES.get(buy_quote.dex, 0.003)
        sell_fee_rate = DEX_FEE_RATES.get(sell_quote.dex, 0.003)

        buy_fee_usd = amount_usd * buy_fee_rate
        sell_fee_usd = amount_usd * sell_fee_rate
        gas_fee_usd = config.GAS_COST_USD * config.TXS_PER_ARB

        total_fees = buy_fee_usd + sell_fee_usd + gas_fee_usd
        net_profit_usd = gross_spread_usd - total_fees
        profitable = net_profit_usd >= config.MIN_PROFIT_USD

        return ArbitrageOpportunity(
            pair=pair,
            amount_base=amount_base,
            amount_usd=amount_usd,
            buy_dex=buy_quote.dex,
            sell_dex=sell_quote.dex,
            buy_price=buy_price,
            sell_price=sell_price,
            gross_spread_usd=gross_spread_usd,
            spread_pct=spread_pct,
            buy_fee_usd=buy_fee_usd,
            sell_fee_usd=sell_fee_usd,
            gas_fee_usd=gas_fee_usd,
            net_profit_usd=net_profit_usd,
            profitable=profitable,
            all_quotes=valid_quotes,
        )

    def simulate(
        self,
        pair_display: str,
        buy_price: float,
        sell_price: float,
        buy_dex: str,
        sell_dex: str,
        amount_usd: float,
    ) -> dict:
        """
        Simulate an arbitrage trade without fetching quotes.
        Useful for manual what-if analysis.
        """
        buy_dex_enum = DEX(buy_dex) if buy_dex in [d.value for d in DEX] else DEX.UNKNOWN
        sell_dex_enum = DEX(sell_dex) if sell_dex in [d.value for d in DEX] else DEX.UNKNOWN

        amount_base = amount_usd / buy_price
        gross = (sell_price - buy_price) * amount_base
        spread_pct = ((sell_price - buy_price) / buy_price) * 100

        buy_fee = amount_usd * DEX_FEE_RATES.get(buy_dex_enum, 0.003)
        sell_fee = amount_usd * DEX_FEE_RATES.get(sell_dex_enum, 0.003)
        gas = config.GAS_COST_USD * config.TXS_PER_ARB

        net = gross - buy_fee - sell_fee - gas

        return {
            "pair": pair_display,
            "amount_usd": amount_usd,
            "buy_dex": buy_dex,
            "sell_dex": sell_dex,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "spread_pct": round(spread_pct, 4),
            "gross_profit_usd": round(gross, 4),
            "buy_fee_usd": round(buy_fee, 4),
            "sell_fee_usd": round(sell_fee, 4),
            "gas_fee_usd": round(gas, 6),
            "total_fees_usd": round(buy_fee + sell_fee + gas, 4),
            "net_profit_usd": round(net, 4),
            "profitable": net >= config.MIN_PROFIT_USD,
            "break_even_spread_pct": round(
                ((buy_fee + sell_fee + gas) / amount_usd) * 100, 4
            ),
        }
