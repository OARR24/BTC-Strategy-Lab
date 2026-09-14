"""
Public documentation — FisherTransform30m

What it contains: A long-only Freqtrade reversal/momentum strategy based on a custom Fisher Transform.
Timeframe: 30m.
Indicators: 10-period Fisher Transform from rolling high/low range and midpoint, one-candle Fisher signal, EMA(50), RSI(14), and 20-candle mean volume.
Entry concept: Looks for Fisher recovering from below -1.0 and crossing its lagged signal upward, with price not far below EMA(50), RSI below 65, and adequate volume.
Exit concept: Exits on Fisher exhaustion after an elevated reading or on a deeper bearish Fisher failure below -1.5 while falling.
ROI / stop-loss: minimal_roi = {"0": 0.08}; stoploss = -0.06.
Limitations: Fixed thresholds and historical-market assumptions can be regime-dependent. Independent validation is required before any practical use.
Status: Experimental / educational code. A backtest does not guarantee future results. This is not financial advice.
Contributions: Reproducible tests, bug reports, technical observations, modifications, and improvement ideas are welcome.
"""

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import numpy as np
import talib.abstract as ta


class FisherTransform30m(IStrategy):
    """
    Fisher Transform 30m

    Objetivo:
    Detectar extremos relativos y posibles cambios de momentum
    mediante Fisher Transform.

    Estrategia de repertorio para análisis de comportamiento.
    """

    INTERFACE_VERSION = 3

    timeframe = "30m"
    can_short = False

    minimal_roi = {
        "0": 0.08
    }

    stoploss = -0.06

    trailing_stop = False

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count = 120

    def populate_indicators(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        period = 10

        highest = dataframe["high"].rolling(period).max()
        lowest = dataframe["low"].rolling(period).min()

        midpoint = (dataframe["high"] + dataframe["low"]) / 2

        price_range = (highest - lowest).replace(0, np.nan)

        raw = (
            2 * ((midpoint - lowest) / price_range - 0.5)
        ).clip(-0.999, 0.999)

        dataframe["fisher"] = (
            0.5 * np.log((1 + raw) / (1 - raw))
        )

        dataframe["fisher_signal"] = (
            dataframe["fisher"].shift(1)
        )

        dataframe["ema50"] = ta.EMA(
            dataframe,
            timeperiod=50
        )

        dataframe["rsi"] = ta.RSI(
            dataframe,
            timeperiod=14
        )

        dataframe["volume_mean_20"] = (
            dataframe["volume"]
            .rolling(20)
            .mean()
        )

        return dataframe

    def populate_entry_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        fisher_reversal = (
            # Fisher venía deprimido
            (dataframe["fisher"].shift(1) < -1.0) &

            # Cruza su señal hacia arriba
            (dataframe["fisher"] >
             dataframe["fisher_signal"]) &
            (dataframe["fisher"].shift(1) <=
             dataframe["fisher_signal"].shift(1)) &

            # Evitar contexto fuertemente bajista
            (dataframe["close"] >
             dataframe["ema50"] * 0.97) &

            # RSI no sobrecomprado
            (dataframe["rsi"] < 65) &

            (dataframe["volume"] >
             dataframe["volume_mean_20"] * 0.70) &

            (dataframe["volume"] > 0)
        )

        dataframe.loc[
            fisher_reversal,
            ["enter_long", "enter_tag"]
        ] = (
            1,
            "FISHER_BULLISH_REVERSAL"
        )

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        # Extremo alcista y giro
        fisher_exhaustion = (
            (dataframe["fisher"].shift(1) > 1.0) &
            (dataframe["fisher"] <
             dataframe["fisher_signal"]) &
            (dataframe["fisher"].shift(1) >=
             dataframe["fisher_signal"].shift(1))
        )

        dataframe.loc[
            fisher_exhaustion,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "FISHER_BULLISH_EXHAUSTION"
        )

        # Pérdida profunda de momentum
        fisher_failure = (
            (dataframe["fisher"] < -1.5) &
            (dataframe["fisher"] <
             dataframe["fisher"].shift(1))
        )

        dataframe.loc[
            fisher_failure,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "FISHER_REVERSAL_FAILURE"
        )

        return dataframe