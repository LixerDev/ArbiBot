"""
Scanner — orchestrates quote fetching, arbitrage detection, and alerting.
"""

import asyncio
import time
from src.models import TokenPair, ScanResult, ArbitrageOpportunity
from src.quotes import QuoteFetcher
from src.calculator import ProfitCalculator
from src.alerter import Alerter
from src.logger import get_logger
from config import config

logger = get_logger(__name__)

# Approximate prices for sizing (updated each scan cycle)
_price_cache: dict[str, float] = {
    "SOL":   165.0,
    "mSOL":  180.0,
    "stSOL": 175.0,
    "ETH":   3400.0,
    "BTC":   65000.0,
    "JUP":   0.85,
    "JTO":   3.5,
    "WIF":   2.2,
    "BONK":  0.000022,
    "PYTH":  0.42,
    "RAY":   2.1,
    "ORCA":  3.8,
    "RNDR":  8.5,
    "USDC":  1.0,
    "USDT":  1.0,
}


class Scanner:
    def __init__(self):
        self.fetcher = QuoteFetcher()
        self.calc = ProfitCalculator()
        self.alerter = Alerter()

    async def scan_pair(self, pair: TokenPair) -> ArbitrageOpportunity | None:
        """Scan a single token pair for arbitrage opportunities."""
        base_price = _price_cache.get(pair.base_symbol, 1.0)
        quotes = await self.fetcher.fetch_all_quotes(pair, config.SCAN_AMOUNT_USD, base_price)

        if len(quotes) < 2:
            return None

        return self.calc.calculate(pair, quotes, config.SCAN_AMOUNT_USD)

    async def scan_all(self, pairs: list[TokenPair]) -> ScanResult:
        """
        Scan all pairs concurrently and return a full ScanResult.
        """
        start = time.time()
        result = ScanResult(pairs_scanned=len(pairs))

        tasks = [self.scan_pair(pair) for pair in pairs]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        opportunities = []
        for opp in raw_results:
            if isinstance(opp, ArbitrageOpportunity):
                opportunities.append(opp)

        result.opportunities = opportunities
        result.profitable_count = sum(1 for o in opportunities if o.profitable)
        result.scan_duration_ms = (time.time() - start) * 1000

        # Send Discord alerts for profitable opportunities
        alert_tasks = [
            self.alerter.send_opportunity_alert(opp)
            for opp in opportunities
            if opp.profitable
        ]
        if alert_tasks:
            await asyncio.gather(*alert_tasks, return_exceptions=True)

        return result

    async def run_watch_loop(self, pairs: list[TokenPair], profitable_only: bool = False):
        """Main watch loop — scans continuously and renders dashboard."""
        from src.dashboard import render_scan
        from src.logger import print_banner

        print_banner()

        console_import = __import__("rich.console", fromlist=["Console"])
        console = console_import.Console()

        console.print(f"[bold]Monitoring {len(pairs)} pairs:[/bold]")
        for p in pairs:
            console.print(f"  • [dim]{p.display}[/dim]")
        console.print(f"\n[dim]Amount per scan: ${config.SCAN_AMOUNT_USD:,.0f} | Min profit: ${config.MIN_PROFIT_USD} | Refresh: {config.REFRESH_INTERVAL}s[/dim]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        while True:
            try:
                result = await self.scan_all(pairs)
                render_scan(result, len(pairs), profitable_only)
                await asyncio.sleep(config.REFRESH_INTERVAL)
            except KeyboardInterrupt:
                console.print("\n[dim]Scanner stopped.[/dim]")
                break
            except Exception as e:
                logger.error(f"Scan loop error: {e}")
                await asyncio.sleep(5)
