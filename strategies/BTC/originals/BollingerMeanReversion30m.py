# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401

"""
Public documentation — BollingerMeanReversion30m

What it contains: A long-only mean-reversion strategy using Bollinger Bands, RSI, and ADX.
Timeframe: 30m.
Indicators: Bollinger Bands(20, 2σ), RSI(14), and ADX(14).
Entry concept: Marks the onset of a condition where price is at/below the lower band, RSI is at/below 30, and ADX is below 25.
Exit concept: Exits when price recovers to or above the Bollinger middle band.
ROI / stop-loss: minimal_roi = {"0": 100.0}; stoploss = -0.02. The original is designed to let the mean-reversion exit signal control normal exits rather than a conventional ROI target.
Limitations: Fixed thresholds and historical-market assumptions can be regime-dependent. Independent validation is required before any practical use.
Status: Experimental / educational code. A backtest does not guarantee future results. This is not financial advice.
Contributions: Reproducible tests, bug reports, technical observations, modifications, and improvement ideas are welcome.
"""

from pandas import DataFrame
import talib.abstract as ta
from freqtrade.strategy import IStrategy


class BollingerMeanReversion30m(IStrategy):
    """
    Baseline de laboratorio: Mean Reversion con Bollinger + RSI + ADX.

    Reglas:
      - Timeframe: 30m
      - Entrada LONG:
          * Precio toca/rompe banda inferior de Bollinger (20, 2 std)
          * RSI(14) <= 30
          * ADX(14) < 25
      - Salida:
          * Precio vuelve a la media de Bollinger
      - Stoploss fijo: -2%
      - Sin trailing
      - Sin ROI objetivo
      - Sin hyperopt
      - Sin filtros extra

    Objetivo:
      Probar una familia distinta a Trend Following durante 1 año
      completo sobre los mismos 10 pares del laboratorio.
    """

    INTERFACE_VERSION = 3

    timeframe = "30m"
    can_short = False
    process_only_new_candles = True

    startup_candle_count = 50

    # Desactivamos take-profit por ROI para dejar que la salida sea
    # exclusivamente el retorno a la media.
    minimal_roi = {"0": 100.0}

    stoploss = -0.02
    trailing_stop = False

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    BB_PERIOD = 20
    BB_STD = 2.0
    RSI_PERIOD = 14
    ADX_PERIOD = 14

    RSI_ENTRY = 30
    ADX_MAX = 25

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bollinger = ta.BBANDS(
            dataframe,
            timeperiod=self.BB_PERIOD,
            nbdevup=self.BB_STD,
            nbdevdn=self.BB_STD,
            matype=0,
        )

        dataframe["bb_upper"] = bollinger["upperband"]
        dataframe["bb_middle"] = bollinger["middleband"]
        dataframe["bb_lower"] = bollinger["lowerband"]

        dataframe["rsi"] = ta.RSI(
            dataframe,
            timeperiod=self.RSI_PERIOD
        )

        dataframe["adx"] = ta.ADX(
            dataframe,
            timeperiod=self.ADX_PERIOD
        )

        # Columnas auxiliares útiles para lectura/gráfico.
        dataframe["distance_to_bb_lower_pct"] = (
            (dataframe["close"] - dataframe["bb_lower"])
            / dataframe["bb_lower"]
            * 100.0
        )

        dataframe["distance_to_bb_middle_pct"] = (
            (dataframe["close"] - dataframe["bb_middle"])
            / dataframe["bb_middle"]
            * 100.0
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entrada LONG cuando el precio entra en sobreextensión bajista
        dentro de un mercado sin tendencia fuerte.
        """
        entry_condition = (
            (dataframe["close"] <= dataframe["bb_lower"])
            & (dataframe["rsi"] <= self.RSI_ENTRY)
            & (dataframe["adx"] < self.ADX_MAX)
            & (dataframe["volume"] > 0)
        )

        # Sólo marcar el inicio de la condición para evitar señales repetidas
        # vela tras vela mientras permanezca bajo la banda.
        prev_condition = (
            entry_condition
            .shift(1)
            .fillna(False)
            .infer_objects(copy=False)
        )

        dataframe.loc[
            entry_condition & (~prev_condition),
            ["enter_long", "enter_tag"],
        ] = (1, "MR_BB_RSI_ADX")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Salida cuando el precio recupera la media de Bollinger.
        """
        exit_condition = (
            (dataframe["close"] >= dataframe["bb_middle"])
            & (dataframe["volume"] > 0)
        )

        dataframe.loc[
            exit_condition,
            ["exit_long", "exit_tag"],
        ] = (1, "MR_RETURN_TO_MEAN")

        return dataframe
