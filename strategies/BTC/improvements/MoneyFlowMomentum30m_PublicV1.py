"""
Public documentation — MoneyFlowMomentum30m_PublicV1

Classification: experimental improvement / research candidate.
What it contains: A limited public evolution of MoneyFlowMomentum30m for independent study. It is not presented as a validated or profitable system.
Timeframe: 30m.
Indicators: MFI(14), EMA(50), EMA(100), RSI(14), and 20-candle relative volume.
Entry concept: Retains the original MFI recovery setup and adds one extra contextual filter: the candidate must either remain below EMA(50) or show relative volume lower than the previous candle.
Exit concept: Retains the original MFI exhaustion and failed-recovery exits.
ROI / stop-loss: minimal_roi = {"0": 0.08}; stoploss = -0.02.
Difference from the public original: one additional entry filter and a tighter fixed stop-loss. No claim is made that these changes generalize outside the historical period in which they were studied.
Limitations: Historical behavior can be period- and regime-dependent; this candidate requires independent out-of-sample and forward validation.
Status: Experimental / educational code. A backtest does not guarantee future results. This is not financial advice.
Contributions: Reproducible tests, bug reports, technical observations, modifications, and improvement ideas are welcome.
"""

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class MoneyFlowMomentum30m_PublicV1(IStrategy):
    """
    Money Flow Momentum 30m

    Objetivo:
    Detectar recuperación de presión compradora mediante
    Money Flow Index (MFI), combinando precio y volumen.

    Estrategia de repertorio para análisis de comportamiento.
    """

    INTERFACE_VERSION = 3

    timeframe = "30m"
    can_short = False

    minimal_roi = {
        "0": 0.08
    }

    stoploss = -0.02

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

        # Money Flow Index
        dataframe["mfi14"] = ta.MFI(
            dataframe,
            timeperiod=14
        )

        # Contexto de tendencia
        dataframe["ema50"] = ta.EMA(
            dataframe,
            timeperiod=50
        )

        dataframe["ema100"] = ta.EMA(
            dataframe,
            timeperiod=100
        )

        # RSI complementario
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

        money_flow_recovery = (
            # MFI venía deprimido
            (dataframe["mfi14"].shift(1) < 30) &

            # Recupera nivel 30
            (dataframe["mfi14"] > 30) &

            # Flujo aumentando
            (dataframe["mfi14"] >
             dataframe["mfi14"].shift(1)) &

            # Contexto no severamente bajista
            (
                (dataframe["ema50"] > dataframe["ema100"]) |
                (dataframe["close"] >
                 dataframe["ema100"] * 0.98)
            ) &

            # RSI confirma recuperación
            (dataframe["rsi"] > 38) &
            (dataframe["rsi"] < 68) &

            # Volumen razonable
            (dataframe["relative_volume"] > 0.80) &

            # Evitar recuperacion extendida con volumen relativo creciente.
            (
                (dataframe['close'] < dataframe['ema50']) |
                (dataframe['relative_volume'] < dataframe['relative_volume'].shift(1))
            ) &

            (dataframe["volume"] > 0)
        )

        dataframe.loc[
            money_flow_recovery,
            ["enter_long", "enter_tag"]
        ] = (
            1,
            "MFI_MONEY_FLOW_RECOVERY"
        )

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        # Flujo entra en zona alta y empieza a caer
        money_flow_exhaustion = (
            (dataframe["mfi14"].shift(1) > 75) &
            (dataframe["mfi14"] <
             dataframe["mfi14"].shift(1))
        )

        dataframe.loc[
            money_flow_exhaustion,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "MFI_MONEY_FLOW_EXHAUSTION"
        )

        # Recuperación falla
        money_flow_failure = (
            (dataframe["mfi14"] < 25) &
            (dataframe["mfi14"].shift(1) >= 25)
        )

        dataframe.loc[
            money_flow_failure,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "MFI_RECOVERY_FAILURE"
        )

        return dataframe