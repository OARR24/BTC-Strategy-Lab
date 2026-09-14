"""
Public documentation — AroonTrend30m

What it contains: A long-only trend-start strategy using Aroon dominance plus momentum and participation checks.
Timeframe: 30m.
Indicators: Aroon(25), Aroon oscillator, RSI(14), ATR(14) with a 30-candle ATR mean, and 20-candle mean volume.
Entry concept: Requires Aroon Up above 75, Aroon Down below 35, the oscillator crossing above 50, RSI between 50 and 75, and sufficient volume.
Exit concept: Exits when Aroon dominance weakens through the 20 level or when Aroon Down becomes dominant while Aroon Up is weak.
ROI / stop-loss: minimal_roi = {"0": 0.10}; stoploss = -0.08.
Limitations: Fixed thresholds and historical-market assumptions can be regime-dependent. Independent validation is required before any practical use.
Status: Experimental / educational code. A backtest does not guarantee future results. This is not financial advice.
Contributions: Reproducible tests, bug reports, technical observations, modifications, and improvement ideas are welcome.
"""

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class AroonTrend30m(IStrategy):
    """
    Aroon Trend 30m

    Objetivo:
    Detectar aparición y persistencia de tendencia alcista
    mediante Aroon Up / Aroon Down.

    Estrategia de repertorio para análisis de comportamiento.
    """

    INTERFACE_VERSION = 3

    timeframe = "30m"
    can_short = False

    minimal_roi = {
        "0": 0.10
    }

    stoploss = -0.08

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

        aroon = ta.AROON(
            dataframe,
            timeperiod=25
        )

        dataframe["aroon_up"] = aroon["aroonup"]
        dataframe["aroon_down"] = aroon["aroondown"]

        dataframe["aroon_osc"] = (
            dataframe["aroon_up"] -
            dataframe["aroon_down"]
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

        dataframe["atr14"] = ta.ATR(
            dataframe,
            timeperiod=14
        )

        dataframe["atr_mean_30"] = (
            dataframe["atr14"]
            .rolling(30)
            .mean()
        )

        return dataframe

    def populate_entry_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        aroon_trend_entry = (
            (dataframe["aroon_up"] > 75) &
            (dataframe["aroon_down"] < 35) &
            (dataframe["aroon_osc"] > 50) &
            (dataframe["aroon_osc"].shift(1) <= 50) &
            (dataframe["rsi"] > 50) &
            (dataframe["rsi"] < 75) &
            (dataframe["volume"] > dataframe["volume_mean_20"] * 0.80) &
            (dataframe["volume"] > 0)
        )

        dataframe.loc[
            aroon_trend_entry,
            ["enter_long", "enter_tag"]
        ] = (
            1,
            "AROON_BULLISH_TREND_START"
        )

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        trend_weakening = (
            (dataframe["aroon_osc"] < 20) &
            (dataframe["aroon_osc"].shift(1) >= 20)
        )

        dataframe.loc[
            trend_weakening,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "AROON_TREND_WEAKENING"
        )

        bearish_dominance = (
            (dataframe["aroon_down"] > 70) &
            (dataframe["aroon_up"] < 40)
        )

        dataframe.loc[
            bearish_dominance,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "AROON_BEARISH_DOMINANCE"
        )

        return dataframe
