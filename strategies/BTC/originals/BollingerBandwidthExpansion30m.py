"""
Public documentation — BollingerBandwidthExpansion30m

What it contains: A long-only volatility-compression-to-expansion breakout strategy.
Timeframe: 30m.
Indicators: Bollinger Bands(20, 2σ), Bollinger relative width and width change, 50-candle mean width, EMA(50), RSI(14), and 20-candle relative volume.
Entry concept: Requires prior Bollinger compression, width beginning to expand, price closing above the upper band and EMA(50), RSI between 50 and 78, and relative volume above 1.0.
Exit concept: Exits when band expansion fades or when price loses the Bollinger middle band.
ROI / stop-loss: minimal_roi = {"0": 0.10}; stoploss = -0.08.
Limitations: Fixed thresholds and historical-market assumptions can be regime-dependent. Independent validation is required before any practical use.
Status: Experimental / educational code. A backtest does not guarantee future results. This is not financial advice.
Contributions: Reproducible tests, bug reports, technical observations, modifications, and improvement ideas are welcome.
"""

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class BollingerBandwidthExpansion30m(IStrategy):
    """
    Bollinger BandWidth Expansion 30m

    Objetivo:
    Detectar compresión de volatilidad y posterior expansión
    alcista mediante el ancho relativo de Bandas de Bollinger.

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

    startup_candle_count = 150

    def populate_indicators(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        bb = ta.BBANDS(
            dataframe,
            timeperiod=20,
            nbdevup=2.0,
            nbdevdn=2.0,
            matype=0
        )

        dataframe["bb_upper"] = bb["upperband"]
        dataframe["bb_middle"] = bb["middleband"]
        dataframe["bb_lower"] = bb["lowerband"]

        # Ancho relativo de las bandas
        dataframe["bb_width"] = (
            (dataframe["bb_upper"] - dataframe["bb_lower"]) /
            dataframe["bb_middle"]
        )

        # Media histórica del ancho
        dataframe["bb_width_mean_50"] = (
            dataframe["bb_width"]
            .rolling(50)
            .mean()
        )

        # Expansión del ancho
        dataframe["bb_width_delta"] = (
            dataframe["bb_width"] -
            dataframe["bb_width"].shift(1)
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

        # Volumen
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

        bandwidth_expansion = (
            # Veníamos de una zona relativamente comprimida
            (dataframe["bb_width"].shift(1) <
             dataframe["bb_width_mean_50"].shift(1) * 0.75) &

            # El ancho empieza a expandirse
            (dataframe["bb_width_delta"] > 0) &
            (dataframe["bb_width_delta"].shift(1) <= 0) &

            # Precio rompe parte alta
            (dataframe["close"] > dataframe["bb_upper"]) &

            # Contexto favorable
            (dataframe["close"] > dataframe["ema50"]) &

            # Momentum razonable
            (dataframe["rsi"] > 50) &
            (dataframe["rsi"] < 78) &

            # Volumen confirma
            (dataframe["relative_volume"] > 1.0) &

            (dataframe["volume"] > 0)
        )

        dataframe.loc[
            bandwidth_expansion,
            ["enter_long", "enter_tag"]
        ] = (
            1,
            "BB_WIDTH_EXPANSION_BREAKOUT"
        )

        return dataframe

    def populate_exit_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        # La expansión pierde fuerza
        bandwidth_fade = (
            (dataframe["bb_width_delta"] < 0) &
            (dataframe["bb_width_delta"].shift(1) >= 0) &
            (dataframe["close"] > dataframe["bb_middle"])
        )

        dataframe.loc[
            bandwidth_fade,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "BB_WIDTH_EXPANSION_FADE"
        )

        # Precio pierde media de Bollinger
        middle_band_loss = (
            (dataframe["close"] < dataframe["bb_middle"]) &
            (dataframe["close"].shift(1) >=
             dataframe["bb_middle"].shift(1))
        )

        dataframe.loc[
            middle_band_loss,
            ["exit_long", "exit_tag"]
        ] = (
            1,
            "BB_MIDDLE_BAND_LOSS"
        )

        return dataframe