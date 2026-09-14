"""
Public documentation — FisherTransform30m_PublicV1

Classification: experimental improvement / research candidate.
What it contains: A limited public evolution of FisherTransform30m for independent study. It is not presented as a validated or profitable system.
Timeframe: 30m.
Indicators: 10-period Fisher Transform from rolling high/low range and midpoint, one-candle Fisher signal, EMA(50), RSI(14), and 20-candle mean volume.
Entry concept: Retains the original Fisher recovery/cross setup and adds one contextual relationship: the candidate must either be at/above EMA(50) or have RSI below its previous-candle value.
Exit concept: Retains the original Fisher exhaustion and deeper bearish-failure exits.
ROI / stop-loss: minimal_roi = {"0": 0.08}; stoploss = -0.06.
Difference from the public original: one additional entry-context filter; ROI, stop-loss, and exit logic remain unchanged from the original.
Limitations: Historical behavior can be period- and regime-dependent; this candidate requires independent out-of-sample and forward validation.
Status: Experimental / educational code. A backtest does not guarantee future results. This is not financial advice.
Contributions: Reproducible tests, bug reports, technical observations, modifications, and improvement ideas are welcome.
"""

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import numpy as np
import talib.abstract as ta


class FisherTransform30m_PublicV1(IStrategy):
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

            # Relacion entre contexto EMA y momento del rebote.
            (
                (dataframe['close'] >= dataframe['ema50']) |
                (dataframe['rsi'] < dataframe['rsi'].shift(1))
            ) &

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