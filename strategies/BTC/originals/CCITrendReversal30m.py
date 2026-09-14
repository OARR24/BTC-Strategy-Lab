"""
Public documentation — CCITrendReversal30m

What it contains: A long-only oversold-recovery strategy centered on CCI.
Timeframe: 30m.
Indicators: CCI(20), EMA(50), EMA(100), RSI(14), ATR(14), and 20-candle mean volume.
Entry concept: Looks for CCI recovering above -100 from a deeply negative reading, improving CCI, non-severely-bearish EMA/price context, RSI between 35 and 65, and sufficient volume.
Exit concept: Exits when CCI turns down after an elevated positive reading or when the recovery fails by crossing back below -100.
ROI / stop-loss: minimal_roi = {"0": 0.08}; stoploss = -0.06.
Limitations: Fixed thresholds and historical-market assumptions can be regime-dependent. Independent validation is required before any practical use.
Status: Experimental / educational code. A backtest does not guarantee future results. This is not financial advice.
Contributions: Reproducible tests, bug reports, technical observations, modifications, and improvement ideas are welcome.
"""

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class CCITrendReversal30m(IStrategy):
    """
    CCI Trend Reversal 30m

    Objetivo:
    Detectar recuperaciones después de una sobreextensión bajista
    usando CCI, dentro de un contexto estructural no severamente bajista.

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

    startup_candle_count = 150

    def populate_indicators(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        # CCI
        dataframe["cci20"] = ta.CCI(
            dataframe,
            timeperiod=20
        )

        # EMA de contexto
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

        # ATR
        dataframe["atr14"] = ta.ATR(
            dataframe,
            timeperiod=14
        )

        # Volumen
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

        cci_recovery = (
            # CCI venía profundamente deprimido
            (dataframe["cci20"].shift(1) < -100) &

            # Recupera -100
            (dataframe["cci20"] > -100) &

            # Mejora respecto a vela anterior
            (dataframe["cci20"] >
             dataframe["cci20"].shift(1)) &

            # Contexto no extremadamente bajista
            (
                (dataframe["ema50"] > dataframe["ema100"]) |
                (
                    dataframe["close"] >
                    dataframe["ema100"] * 0.97
                )
            ) &

            # RSI confirma recuperación
            (dataframe["rsi"] > 35) &
            (dataframe["rsi"] < 65) &

            # Volumen mínimo
            (dataframe["volume"] >
             dataframe["volume_mean_20"] * 0.70) &

            (dataframe["volume"] > 0)
        )

        dataframe.loc[
            cci_recovery,
            ["enter_long", "enter_tag"]
        ] = (
            1,
            "CCI_OVERSOLD_RECOVERY"
        )

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        # CCI alcanza zona positiva y empieza a girar
        cci_target = (
            (dataframe["cci20"].shift(1) > 100) &
            (dataframe["cci20"] <
             dataframe["cci20"].shift(1))
        )

        dataframe.loc[
            cci_target,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "CCI_POSITIVE_EXHAUSTION"
        )

        # Recuperación falla y vuelve debajo de -100
        cci_failure = (
            (dataframe["cci20"] < -100) &
            (dataframe["cci20"].shift(1) >= -100)
        )

        dataframe.loc[
            cci_failure,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "CCI_RECOVERY_FAILURE"
        )

        return dataframe