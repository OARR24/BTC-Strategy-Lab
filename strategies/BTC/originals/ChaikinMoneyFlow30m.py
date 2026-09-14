"""
Public documentation — ChaikinMoneyFlow30m

What it contains: A long-only accumulation/flow strategy using a manually calculated Chaikin Money Flow.
Timeframe: 30m.
Indicators: CMF(20) and its one-candle change, EMA(50), RSI(14), and 20-candle relative volume.
Entry concept: Looks for CMF crossing above +0.05 while flow is increasing, price is above EMA(50), RSI is between 48 and 72, and relative volume is above 0.90.
Exit concept: Exits when positive buying pressure begins to fade under the strategy's RSI condition or when CMF crosses into distribution below -0.05.
ROI / stop-loss: minimal_roi = {"0": 0.08}; stoploss = -0.06.
Limitations: Fixed thresholds and historical-market assumptions can be regime-dependent. Independent validation is required before any practical use.
Status: Experimental / educational code. A backtest does not guarantee future results. This is not financial advice.
Contributions: Reproducible tests, bug reports, technical observations, modifications, and improvement ideas are welcome.
"""

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import numpy as np
import talib.abstract as ta


class ChaikinMoneyFlow30m(IStrategy):
    """
    Chaikin Money Flow 30m

    Objetivo:
    Detectar entrada de presión compradora mediante CMF
    y capturar continuación mientras el flujo permanezca positivo.

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

        # Money Flow Multiplier
        candle_range = (
            dataframe["high"] -
            dataframe["low"]
        ).replace(0, np.nan)

        dataframe["mf_multiplier"] = (
            (
                (dataframe["close"] - dataframe["low"]) -
                (dataframe["high"] - dataframe["close"])
            ) / candle_range
        )

        # Money Flow Volume
        dataframe["mf_volume"] = (
            dataframe["mf_multiplier"] *
            dataframe["volume"]
        )

        # Chaikin Money Flow 20
        dataframe["cmf20"] = (
            dataframe["mf_volume"].rolling(20).sum() /
            dataframe["volume"].rolling(20).sum()
        )

        # Cambio de CMF
        dataframe["cmf_delta"] = (
            dataframe["cmf20"] -
            dataframe["cmf20"].shift(1)
        )

        # Contexto
        dataframe["ema50"] = ta.EMA(
            dataframe,
            timeperiod=50
        )

        dataframe["rsi"] = ta.RSI(
            dataframe,
            timeperiod=14
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

        return dataframe

    def populate_entry_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        cmf_accumulation = (
            # CMF cruza a presión compradora
            (dataframe["cmf20"] > 0.05) &
            (dataframe["cmf20"].shift(1) <= 0.05) &

            # Flujo creciendo
            (dataframe["cmf_delta"] > 0) &

            # Precio en contexto favorable
            (dataframe["close"] > dataframe["ema50"]) &

            # RSI con fuerza moderada
            (dataframe["rsi"] > 48) &
            (dataframe["rsi"] < 72) &

            # Participación suficiente
            (dataframe["relative_volume"] > 0.90) &

            (dataframe["volume"] > 0)
        )

        dataframe.loc[
            cmf_accumulation,
            ["enter_long", "enter_tag"]
        ] = (
            1,
            "CMF_ACCUMULATION_START"
        )

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        # El flujo comprador pierde fuerza,
        # pero todavía estamos por encima de cero
        cmf_fade = (
            (dataframe["cmf20"] > 0) &
            (dataframe["cmf_delta"] < 0) &
            (dataframe["cmf_delta"].shift(1) >= 0) &
            (dataframe["rsi"] > 62)
        )

        dataframe.loc[
            cmf_fade,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "CMF_BUYING_PRESSURE_FADE"
        )

        # El CMF pasa claramente a presión vendedora
        cmf_distribution = (
            (dataframe["cmf20"] < -0.05) &
            (dataframe["cmf20"].shift(1) >= -0.05)
        )

        dataframe.loc[
            cmf_distribution,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "CMF_DISTRIBUTION"
        )

        return dataframe