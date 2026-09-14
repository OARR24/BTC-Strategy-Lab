# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401

"""
Public documentation — ADXEMAPullback30m

What it contains: A long-only trend-pullback strategy for Freqtrade.
Timeframe: 30m.
Indicators: EMA(20), EMA(50), EMA(200), and ADX(14).
Entry concept: Requires EMA(50) above EMA(200) and ADX above 25, then looks for a pullback around EMA(20)/EMA(50) followed by a bullish recovery close back above EMA(20).
Exit concept: Exits when price closes below EMA(50) or EMA(50) falls below EMA(200).
ROI / stop-loss: minimal_roi = {"0": 100.0}; stoploss = -0.99. The original relies primarily on exit signals rather than a normal fixed ROI target.
Limitations: Fixed thresholds and historical-market assumptions can be regime-dependent. Independent validation is required before any practical use.
Status: Experimental / educational code. A backtest does not guarantee future results. This is not financial advice.
Contributions: Reproducible tests, bug reports, technical observations, modifications, and improvement ideas are welcome.
"""

from pandas import DataFrame
import talib.abstract as ta

from freqtrade.strategy import IStrategy


class ADXEMAPullback30m(IStrategy):
    """
    ADX + EMA Pullback - baseline de laboratorio.

    IDEA
    ----
    Operar retrocesos dentro de una tendencia alcista confirmada,
    evitando entrar únicamente por cruce o expansión tardía.

    TIMEFRAME
    ---------
    30m

    INDICADORES
    -----------
    EMA20
    EMA50
    EMA200
    ADX(14)

    ENTRADA LONG
    ------------
    - EMA50 > EMA200
    - ADX(14) > 25
    - precio retrocede hacia zona EMA20/EMA50
    - vela actual recupera y cierra por encima de EMA20
    - señal sólo en la recuperación, no durante todo el retroceso

    SALIDA
    ------
    - close < EMA50
      o
    - EMA50 < EMA200

    Notas:
        - Spot / LONG únicamente.
        - Sin short.
        - Sin ROI fijo.
        - Sin trailing.
        - Sin hyperopt.
        - Sin filtros adicionales.
        - Objetivo: medir la lógica base durante 1 año completo.
    """

    INTERFACE_VERSION = 3

    timeframe = "30m"
    can_short = False

    process_only_new_candles = True
    startup_candle_count = 250

    minimal_roi = {"0": 100.0}
    stoploss = -0.99
    trailing_stop = False

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    EMA_FAST = 20
    EMA_TREND = 50
    EMA_SLOW = 200

    ADX_PERIOD = 14
    ADX_MIN = 25

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(
            dataframe,
            timeperiod=self.EMA_FAST
        )

        dataframe["ema50"] = ta.EMA(
            dataframe,
            timeperiod=self.EMA_TREND
        )

        dataframe["ema200"] = ta.EMA(
            dataframe,
            timeperiod=self.EMA_SLOW
        )

        dataframe["adx"] = ta.ADX(
            dataframe,
            timeperiod=self.ADX_PERIOD
        )

        dataframe["trend_up"] = (
            dataframe["ema50"] > dataframe["ema200"]
        ).astype(int)

        # Distancia útil para análisis posterior.
        dataframe["distance_ema20_pct"] = (
            (dataframe["close"] - dataframe["ema20"])
            / dataframe["ema20"]
            * 100.0
        )

        dataframe["distance_ema50_pct"] = (
            (dataframe["close"] - dataframe["ema50"])
            / dataframe["ema50"]
            * 100.0
        )

        # Retroceso:
        # la vela toca o penetra EMA20 pero no rompe claramente EMA50.
        dataframe["pullback_zone"] = (
            (dataframe["low"] <= dataframe["ema20"])
            & (dataframe["low"] >= dataframe["ema50"] * 0.995)
        ).astype(int)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entrada al recuperar EMA20 después de un retroceso.
        """
        previous_pullback = (
            (dataframe["low"].shift(1) <= dataframe["ema20"].shift(1))
            & (dataframe["low"].shift(1) >= dataframe["ema50"].shift(1) * 0.995)
        )

        recovery = (
            (dataframe["close"] > dataframe["ema20"])
            & (dataframe["close"].shift(1) <= dataframe["ema20"].shift(1))
        )

        entry_condition = (
            (dataframe["ema50"] > dataframe["ema200"])
            & (dataframe["adx"] > self.ADX_MIN)
            & previous_pullback
            & recovery
            & (dataframe["close"] > dataframe["open"])
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[
            entry_condition,
            ["enter_long", "enter_tag"],
        ] = (1, "ADX_EMA_PULLBACK_LONG")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Salida cuando se pierde la estructura de tendencia.
        """
        exit_condition = (
            (
                (dataframe["close"] < dataframe["ema50"])
                | (dataframe["ema50"] < dataframe["ema200"])
            )
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[
            exit_condition,
            ["exit_long", "exit_tag"],
        ] = (1, "ADX_EMA_TREND_LOST")

        return dataframe
