"""
Dashboard — Rich terminal display for ArbiBot.
"""

from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from src.models import ScanResult, ArbitrageOpportunity, DEX, DEX_COLORS
from config import config

console = Console()


def _price_str(price: float) -> str:
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:,.4f}"
    elif price >= 0.001:
        return f"${price:,.6f}"
    return f"${price:.8f}"


def _profit_color(net: float) -> str:
    if net >= config.MIN_PROFIT_USD:
        return "bold green"
    elif net >= 0:
        return "yellow"
    return "red"


def render_scan(result: ScanResult, pairs_count: int, profitable_only: bool = False):
    """Render a full scan result to the terminal."""
    now = datetime.utcnow().strftime("%H:%M:%S UTC")
    console.clear()
    console.rule(
        f"[bold]⚡ ArbiBot[/bold]  [dim]{pairs_count} pairs  |  "
        f"refresh: {config.REFRESH_INTERVAL}s  |  {now}[/dim]"
    )

    profitable = [o for o in result.opportunities if o.profitable]
    console.print(
        f"  [dim]Scan: {result.scan_duration_ms:.0f}ms  |  "
        f"[green]Profitable: {len(profitable)}[/green]  |  "
        f"Amount: ${config.SCAN_AMOUNT_USD:,.0f}  |  "
        f"Min profit: ${config.MIN_PROFIT_USD:.2f}[/dim]\n"
    )

    opps = [o for o in result.opportunities if o.profitable] if profitable_only else result.opportunities
    if not opps:
        console.print("[dim]No opportunities found yet. Scanning...[/dim]")
        return

    table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1), expand=True)
    table.add_column("Pair", style="bold", width=14)
    table.add_column("Raydium", justify="right", width=16)
    table.add_column("Orca", justify="right", width=16)
    table.add_column("Jupiter", justify="right", width=16)
    table.add_column("Spread", justify="right", width=10)
    table.add_column("Net Profit", justify="right", width=14)
    table.add_column("Route", width=22)

    for opp in sorted(opps, key=lambda o: -o.net_profit_usd):
        # Build price cells per DEX
        price_by_dex = {q.dex: q.effective_price for q in opp.all_quotes}

        def dex_cell(dex: DEX) -> str:
            p = price_by_dex.get(dex, 0)
            if p == 0:
                return "[dim]—[/dim]"
            is_best_sell = (dex == opp.sell_dex)
            is_best_buy = (dex == opp.buy_dex)
            color = DEX_COLORS.get(dex, "white")
            marker = " ▲" if is_best_sell else (" ▼" if is_best_buy else "")
            return f"[{color}]{_price_str(p)}{marker}[/{color}]"

        spread_color = "green" if opp.spread_pct > 0.2 else ("yellow" if opp.spread_pct > 0.1 else "dim")
        profit_color = _profit_color(opp.net_profit_usd)

        route = f"{opp.buy_dex.value[:6]} → {opp.sell_dex.value[:6]}"

        table.add_row(
            opp.pair.display,
            dex_cell(DEX.RAYDIUM),
            dex_cell(DEX.ORCA),
            dex_cell(DEX.JUPITER),
            f"[{spread_color}]{opp.spread_pct:.3f}%[/{spread_color}]",
            f"[{profit_color}]${opp.net_profit_usd:+,.4f}[/{profit_color}]",
            f"[dim]{route}[/dim]",
        )

    console.print(table)

    # Best opportunity detail
    best = result.best_opportunity
    if best:
        _render_opportunity_detail(best)

    console.print()


def _render_opportunity_detail(opp: ArbitrageOpportunity):
    """Render a detailed breakdown of the best opportunity."""
    profit_color = _profit_color(opp.net_profit_usd)
    total_fees = opp.buy_fee_usd + opp.sell_fee_usd + opp.gas_fee_usd

    lines = [
        f"  [bold]Pair:[/bold]         {opp.pair.display}",
        f"  [bold]Amount:[/bold]       {opp.amount_base:.4f} {opp.pair.base_symbol}  (${opp.amount_usd:,.2f})",
        f"  [bold]Buy on:[/bold]       [cyan]{opp.buy_dex.value}[/cyan]  →  {_price_str(opp.buy_price)} / {opp.pair.base_symbol}",
        f"  [bold]Sell on:[/bold]      [blue]{opp.sell_dex.value}[/blue]  →  {_price_str(opp.sell_price)} / {opp.pair.base_symbol}",
        f"  [bold]Spread:[/bold]       {opp.spread_pct:.4f}%",
        f"  [bold]Gross Profit:[/bold] ${opp.gross_spread_usd:,.4f}",
        f"  [bold]Fees:[/bold]         -${opp.buy_fee_usd:.4f} ({opp.buy_dex.value}) -${opp.sell_fee_usd:.4f} ({opp.sell_dex.value}) -${opp.gas_fee_usd:.4f} (gas)",
        f"  [bold]Net Profit:[/bold]   [{profit_color}]${opp.net_profit_usd:+,.4f}[/{profit_color}]  {'✅ PROFITABLE' if opp.profitable else '❌ Not profitable'}",
    ]

    console.print(Panel(
        "\n".join(lines),
        title="[bold]⚡ Best Opportunity[/bold]",
        border_style="green" if opp.profitable else "dim"
    ))
