"""
Alerter — sends Discord alerts for profitable arbitrage opportunities.
"""

import aiohttp
import time
from src.models import ArbitrageOpportunity, DEX
from src.logger import get_logger
from config import config

logger = get_logger(__name__)

_last_alert: dict[str, float] = {}


class Alerter:
    def __init__(self):
        self.webhook = config.DISCORD_WEBHOOK_URL
        self.cooldown = config.ALERT_COOLDOWN_MINUTES * 60

    def _should_alert(self, pair_key: str) -> bool:
        last = _last_alert.get(pair_key, 0)
        return (time.time() - last) > self.cooldown

    def _record(self, pair_key: str):
        _last_alert[pair_key] = time.time()

    async def send_opportunity_alert(self, opp: ArbitrageOpportunity):
        if not self.webhook:
            return
        if not self._should_alert(opp.pair.display):
            return

        color = 0x00FF88 if opp.profitable else 0xFF4444

        buy_fee = opp.buy_fee_usd
        sell_fee = opp.sell_fee_usd
        total_fees = buy_fee + sell_fee + opp.gas_fee_usd

        embed = {
            "title": f"⚡ ARBITRAGE OPPORTUNITY — {opp.pair.display}",
            "color": color,
            "fields": [
                {"name": "Trade Size", "value": f"${opp.amount_usd:,.2f} ({opp.amount_base:.4f} {opp.pair.base_symbol})", "inline": True},
                {"name": "Spread", "value": f"{opp.spread_pct:.4f}%", "inline": True},
                {"name": "\u200b", "value": "\u200b", "inline": True},
                {"name": f"Buy on {opp.buy_dex.value}", "value": f"${opp.buy_price:,.6f}", "inline": True},
                {"name": f"Sell on {opp.sell_dex.value}", "value": f"${opp.sell_price:,.6f}", "inline": True},
                {"name": "\u200b", "value": "\u200b", "inline": True},
                {"name": "Gross Profit", "value": f"${opp.gross_spread_usd:,.4f}", "inline": True},
                {"name": "Total Fees", "value": f"-${total_fees:,.4f}", "inline": True},
                {"name": "Net Profit", "value": f"**${opp.net_profit_usd:+,.4f}**", "inline": True},
                {
                    "name": "Execute",
                    "value": (
                        f"1. Buy {opp.amount_base:.4f} {opp.pair.base_symbol} on **{opp.buy_dex.value}**\n"
                        f"2. Sell {opp.amount_base:.4f} {opp.pair.base_symbol} on **{opp.sell_dex.value}**"
                    ),
                    "inline": False
                },
            ],
            "footer": {"text": "ArbiBot by LixerDev • Solana Cross-DEX Arbitrage Detector"},
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook,
                    json={"embeds": [embed]},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status in (200, 204):
                        logger.info(f"Discord alert sent for {opp.pair.display}")
                        self._record(opp.pair.display)
        except Exception as e:
            logger.error(f"Discord alert failed: {e}")
