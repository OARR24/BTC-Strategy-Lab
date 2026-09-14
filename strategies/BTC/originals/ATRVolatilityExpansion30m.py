"""
Public documentation — ATRVolatilityExpansion30m

What it contains: A long-only volatility-expansion / breakout strategy.
Timeframe: 30m.
Indicators/features: ATR(14), 30-candle mean ATR, ATR ratio, prior 20-candle high/low, candle-range ratio, 20-candle relative volume, and RSI(14).
Entry concept: Looks for ATR and candle-range expansion, a bullish close above the prior 20-candle high, above-normal volume, and RSI between 50 and 78.
Exit concept: Exits when ATR expansion normalizes through its baseline or when the breakout fails and price returns below the prior-high reference.
ROI / stop-loss: minimal_roi = {"0": 0.10}; stoploss = -0.08.
Limitations: Fixed thresholds and historical-market assumptions can be regime-dependent. Independent validation is required before any practical use.
Status: Experimental / educational code. A backtest does not guarantee future results. This is not financial advice.
Contributions: Reproducible tests, bug reports, technical observations, modifications, and improvement ideas are welcome.
"""

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class ATRVolatilityExpansion30m(IStrategy):
    """
    ATR Volatility Expansion 30m

    Objetivo:
    Detectar expansión anormal de volatilidad acompañada
    por ruptura de máximos recientes.

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

        # ATR actual
        dataframe["atr14"] = ta.ATR(
            dataframe,
            timeperiod=14
        )

        # Régimen medio de ATR
        dataframe["atr_mean_30"] = (
            dataframe["atr14"]
            .rolling(30)
            .mean()
        )

        # ATR relativo
        dataframe["atr_ratio"] = (
            dataframe["atr14"] /
            dataframe["atr_mean_30"]
        )

        # Máximo previo de 20 velas
        dataframe["high_20"] = (
            dataframe["high"]
            .rolling(20)
            .max()
            .shift(1)
        )

        # Mínimo previo
        dataframe["low_20"] = (
            dataframe["low"]
            .rolling(20)
            .min()
            .shift(1)
        )

        # Rango de vela
        dataframe["candle_range"] = (
            dataframe["high"] -
            dataframe["low"]
        )

        dataframe["range_mean_20"] = (
            dataframe["candle_range"]
            .rolling(20)
            .mean()
        )

        dataframe["range_ratio"] = (
            dataframe["candle_range"] /
            dataframe["range_mean_20"]
        )

        # Volumen relativo
        dataframe["volume_mean_20"] = (
            dataframe["volume"]
            .rolling(20)
            .mean()
        )

        dataframe["relative_volume"] = (
            dataframe["volume"] /
            dataframe["volume_mean_20"]
        )

        # RSI sólo para evitar entrada extrema
        dataframe["rsi"] = ta.RSI(
            dataframe,
            timeperiod=14
        )

        return dataframe

    def populate_entry_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        expansion_entry = (
            # ATR claramente expandido
            (dataframe["atr_ratio"] > 1.20) &

            # Vela actual también mayor de lo normal
            (dataframe["range_ratio"] > 1.30) &

            # Ruptura de máximo reciente
            (dataframe["close"] > dataframe["high_20"]) &

            # Vela alcista
            (dataframe["close"] > dataframe["open"]) &

            # Volumen superior al normal
            (dataframe["relative_volume"] > 1.10) &

            # Evitar entrar demasiado tarde
            (dataframe["rsi"] > 50) &
            (dataframe["rsi"] < 78) &

            (dataframe["volume"] > 0)
        )

        dataframe.loc[
            expansion_entry,
            ["enter_long", "enter_tag"]
        ] = (
            1,
            "ATR_VOLATILITY_EXPANSION"
        )

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        # La expansión de ATR se agota
        volatility_normalization = (
            (dataframe["atr_ratio"] < 1.0) &
            (dataframe["atr_ratio"].shift(1) >= 1.0)
        )

        dataframe.loc[
            volatility_normalization,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "ATR_VOLATILITY_NORMALIZATION"
        )

        # Falla la ruptura y vuelve al rango anterior
        breakout_failure = (
            (dataframe["close"] < dataframe["high_20"]) &
            (dataframe["close"].shift(1) >=
             dataframe["high_20"].shift(1))
        )

        dataframe.loc[
            breakout_failure,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "ATR_BREAKOUT_FAILURE"
        )

        return dataframe