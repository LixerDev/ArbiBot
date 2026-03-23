#!/usr/bin/env python3
"""
ArbiBot — Cross-DEX Arbitrage Detector for Solana
Compares Raydium, Orca, and Jupiter in real time.
Built by LixerDev
"""

import asyncio
import json
from typing import Optional
import typer
from rich.console import Console

from config import config
from src.logger import get_logger, print_banner
from src.models import TokenPair, TOKEN_MINTS
from src.scanner import Scanner
from src.calculator import ProfitCalculator
from src.quotes import QuoteFetcher

app = typer.Typer(
    help="ArbiBot — Real-time cross-DEX arbitrage detector for Solana",
    no_args_is_help=True
)
console = Console()
logger = get_logger(__name__)


def _parse_pairs(pair_strs: list[str]) -> list[TokenPair]:
    pairs = []
    for s in pair_strs:
        s = s.strip().upper()
        if "/" in s:
            base, quote = s.split("/", 1)
            if base not in TOKEN_MINTS:
                console.print(f"[yellow]Unknown token: {base} — skipping[/yellow]")
                continue
            if quote not in TOKEN_MINTS:
                console.print(f"[yellow]Unknown token: {quote} — skipping[/yellow]")
                continue
            pairs.append(TokenPair(base_symbol=base, quote_symbol=quote))
    return pairs


def _get_default_pairs() -> list[TokenPair]:
    return _parse_pairs([f"{b}/{q}" for b, q in config.default_pairs])


@app.command()
def watch(
    pairs: list[str] = typer.Option([], "--pairs", "-p", help="Pairs to watch (e.g. SOL/USDC)"),
    profitable_only: bool = typer.Option(False, "--profitable-only", help="Only show profitable opportunities"),
    amount: Optional[float] = typer.Option(None, "--amount", "-a", help="Override scan amount in USD"),
    interval: Optional[int] = typer.Option(None, "--interval", "-i", help="Override refresh interval (seconds)"),
):
    """Live scanner — continuously monitors pairs and shows arbitrage dashboard."""
    if amount:
        config.SCAN_AMOUNT_USD = amount
    if interval:
        config.REFRESH_INTERVAL = interval

    token_pairs = _parse_pairs(pairs) if pairs else _get_default_pairs()
    if not token_pairs:
        console.print("[red]No valid pairs to monitor.[/red]")
        raise typer.Exit(1)

    scanner = Scanner()
    asyncio.run(scanner.run_watch_loop(token_pairs, profitable_only=profitable_only))


@app.command()
def scan(
    pairs: list[str] = typer.Option([], "--pairs", "-p", help="Pairs to scan"),
    amount: Optional[float] = typer.Option(None, "--amount", "-a", help="Scan amount in USD"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Export JSON"),
    profitable_only: bool = typer.Option(False, "--profitable-only"),
):
    """One-time scan — check all pairs once and show results."""
    print_banner()

    if amount:
        config.SCAN_AMOUNT_USD = amount

    token_pairs = _parse_pairs(pairs) if pairs else _get_default_pairs()

    async def _run():
        from src.dashboard import render_scan
        scanner = Scanner()
        console.print(f"[dim]Scanning {len(token_pairs)} pairs @ ${config.SCAN_AMOUNT_USD:,.0f}...[/dim]")
        result = await scanner.scan_all(token_pairs)
        render_scan(result, len(token_pairs), profitable_only)

        if output:
            data = [o.to_dict() for o in result.opportunities]
            with open(output, "w") as f:
                json.dump(data, f, indent=2)
            console.print(f"[dim]Results exported to {output}[/dim]")

    asyncio.run(_run())


@app.command()
def simulate(
    pair: str = typer.Option(..., "--pair", "-p", help="Pair to simulate (e.g. SOL/USDC)"),
    buy_price: float = typer.Option(..., "--buy-price", help="Buy price (on cheaper DEX)"),
    sell_price: float = typer.Option(..., "--sell-price", help="Sell price (on expensive DEX)"),
    buy_dex: str = typer.Option("Orca", "--buy-dex", help="Buy DEX name"),
    sell_dex: str = typer.Option("Raydium", "--sell-dex", help="Sell DEX name"),
    amount: float = typer.Option(1000.0, "--amount", "-a", help="Trade amount in USD"),
):
    """
    Simulate a hypothetical arbitrage — calculate profit without fetching quotes.
    Useful for manual what-if analysis.
    """
    print_banner()
    calc = ProfitCalculator()
    result = calc.simulate(pair, buy_price, sell_price, buy_dex, sell_dex, amount)

    console.print(f"\n[bold]🔢 Arbitrage Simulation — {pair}[/bold]\n")
    console.print(f"  Trade Size:         ${result['amount_usd']:,.2f}")
    console.print(f"  Buy {buy_dex:10s}     ${result['buy_price']:,.6f}")
    console.print(f"  Sell {sell_dex:9s}     ${result['sell_price']:,.6f}")
    console.print(f"  Spread:             {result['spread_pct']:.4f}%")
    console.print(f"  Break-even spread:  {result['break_even_spread_pct']:.4f}%")
    console.print(f"  Gross Profit:       ${result['gross_profit_usd']:,.4f}")
    console.print(f"  Total Fees:         -${result['total_fees_usd']:,.4f}")
    color = "green" if result["profitable"] else "red"
    status = "✅ PROFITABLE" if result["profitable"] else "❌ Not profitable"
    console.print(f"  Net Profit:         [{color}]${result['net_profit_usd']:+,.4f}  {status}[/{color}]")
    console.print()


@app.command()
def tokens():
    """List all supported tokens and their mint addresses."""
    from rich.table import Table
    from rich import box as rbox

    print_banner()
    table = Table(box=rbox.ROUNDED, title="Supported Tokens")
    table.add_column("Symbol", style="bold")
    table.add_column("Mint Address")

    for symbol, mint in TOKEN_MINTS.items():
        table.add_row(symbol, f"[dim]{mint}[/dim]")

    console.print(table)


if __name__ == "__main__":
    app()
