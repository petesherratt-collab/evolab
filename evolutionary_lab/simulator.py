from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import mean
from time import perf_counter
from typing import Sequence

from .types import BacktestResult, MarketBar, StrategySpec


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    initial_capital: float = 1_000.0
    fee_bps: int = 5

    def __post_init__(self) -> None:
        if not math.isfinite(self.initial_capital) or self.initial_capital <= 0:
            raise ValueError("INVALID_INITIAL_CAPITAL")
        if not 0 <= self.fee_bps <= 1_000:
            raise ValueError("FEE_OUT_OF_RANGE")


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


class DeterministicBacktester:
    """Long/flat moving-average strategies with explicit one-step execution lag."""

    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()

    def run(self, bars: Sequence[MarketBar], strategy: StrategySpec) -> BacktestResult:
        started = perf_counter()
        if len(bars) <= strategy.slow_window + 1:
            raise ValueError("MARKET_TOO_SHORT_FOR_STRATEGY")

        equity = self.config.initial_capital
        peak = equity
        position = 0.0
        max_drawdown = 0.0
        turnover = 0.0
        trades = 0
        observations = 0
        data_latencies = [bar.available_at_ms - bar.timestamp_ms for bar in bars]
        fee_rate = self.config.fee_bps / 10_000

        # A signal at bar i is based only on bars available by bar i's timestamp.
        # The selected position earns the close-to-close return from i to i+1.
        for index in range(strategy.slow_window, len(bars) - 1):
            current = bars[index]
            available_history = [
                bar
                for bar in bars[: index + 1]
                if bar.available_at_ms <= current.timestamp_ms
            ]
            if len(available_history) < strategy.slow_window:
                continue

            fast = mean(bar.close for bar in available_history[-strategy.fast_window :])
            slow = mean(bar.close for bar in available_history[-strategy.slow_window :])
            entry_level = slow * (1 + strategy.entry_threshold_bps / 10_000)
            exit_level = slow * (1 - strategy.exit_threshold_bps / 10_000)

            target = position
            if position == 0.0 and fast > entry_level:
                target = strategy.max_position_bps / 10_000
            elif position > 0.0 and fast < exit_level:
                target = 0.0

            next_close_return = bars[index + 1].close / current.close - 1
            trade_fraction = abs(target - position)
            fee = equity * trade_fraction * fee_rate
            equity = max(0.0, equity * (1 + target * next_close_return) - fee)
            turnover += trade_fraction
            if trade_fraction > 0:
                trades += 1
            position = target
            observations += 1

            peak = max(peak, equity)
            drawdown = 0.0 if peak == 0 else (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)
            if equity == 0.0:
                break

        if observations == 0:
            raise ValueError("NO_BACKTEST_OBSERVATIONS")
        ending = equity
        return BacktestResult(
            strategy_id=strategy.strategy_id(),
            starting_capital=self.config.initial_capital,
            ending_capital=ending,
            net_return=ending / self.config.initial_capital - 1,
            max_drawdown=max_drawdown,
            turnover=turnover,
            observations=observations,
            trades=trades,
            bankrupt=ending <= 0.0,
            data_latency_ms_p50=_percentile(data_latencies, 0.50),
            data_latency_ms_p95=_percentile(data_latencies, 0.95),
            evaluation_ms=(perf_counter() - started) * 1_000,
        )
