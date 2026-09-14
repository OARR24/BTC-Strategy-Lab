"""
Public documentation — MoneyFlowMomentum30m

What it contains: A long-only Freqtrade momentum/recovery strategy combining price, volume, and money-flow context.
Timeframe: 30m.
Indicators: MFI(14), EMA(50), EMA(100), RSI(14), and 20-candle relative volume.
Entry concept: Looks for MFI recovering above 30 from a depressed reading while money flow rises, broader EMA/price context is not severely bearish, RSI is between 38 and 68, and relative volume is above 0.80.
Exit concept: Exits when elevated MFI begins to fade or when the recovery fails by crossing back below 25.
ROI / stop-loss: minimal_roi = {"0": 0.08}; stoploss = -0.06.
Limitations: Fixed thresholds and historical-market assumptions can be regime-dependent. Independent validation is required before any practical use.
Status: Experimental / educational code. A backtest does not guarantee future results. This is not financial advice.
Contributions: Reproducible tests, bug reports, technical observations, modifications, and improvement ideas are welcome.
"""

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class MoneyFlowMomentum30m(IStrategy):
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