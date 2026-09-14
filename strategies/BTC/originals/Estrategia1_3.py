# pragma pylint: disable=missing-docstring, invalid-name

"""
Public documentation — Estrategia1_3

What it contains: A long-only Freqtrade research strategy with several switchable entry/exit paths built from 30-minute OHLCV data.
Timeframe: 30m.
Indicators/features: EMA-style structures over 8 and 48 candles, rolling linear-trend estimates over the same windows, slope/step measurements, 90-minute projections, candle-body/wick structure, and a multi-line structural spread.
Entry concept: The original file contains multiple switchable entry families. In its current original configuration, the enabled path arms on rising short-horizon structures and a projected pre-cross, then waits for a bullish turn in the longer trend proxy plus structural confirmation before entering.
Exit concept: The original file can signal a projected 90-minute cross, a real short-horizon trend/EMA cross, or loss of context. Its exit-confirmation logic may defer controlled exits until rebound conditions are met; Freqtrade safety exits are not blocked.
ROI / stop-loss: minimal_roi = {"0": 0.99}; stoploss = -0.99.
Limitations: The names "4h" and "1d" in this strategy are derived from 30m windows rather than separate informative-timeframe candles. The rules are stateful and research-oriented.
Status: Experimental / educational code. A backtest does not guarantee future results. This is not financial advice.
Contributions: Reproducible tests, bug reports, technical observations, modifications, and improvement ideas are welcome.
"""

from freqtrade.strategy import IStrategy
import pandas as pd
from pandas import DataFrame
import numpy as np


class Estrategia1_3(IStrategy):
    """
    Estrategia 1 v1.3 — Laboratorio con interruptores independientes.

    Entradas disponibles:
    - Entrada Base
    - Entrada 1 EXTRAP 1h30
    - Entrada 2 Alineación 4h / 1d

    Salidas disponibles:
    - Salida EXTRAP 1h30
    - Salida Cruce 4h real
    - Salida Contexto perdido

    Cada entrada y salida puede activarse/desactivarse
    independientemente mediante los interruptores de laboratorio.
    """

    # ============================================================
    # INTERRUPTORES DE LABORATORIO
    # ============================================================
    #
    # CONFIGURACIÓN ACTUAL:
    #
    # Entrada Base      = OFF
    # Entrada 1 EXTRAP  = ON
    # Entrada 2         = OFF
    #
    # Salida EXTRAP     = ON
    # Salida Cruce 4h   = ON
    # Salida Contexto   = ON
    #
    # Las salidas de seguridad propias de Freqtrade
    # NO se desactivan con estos interruptores.
    # ============================================================

    # ENTRADAS
    ENTRADA_BASE_HABILITADA = False
    ENTRADA_1_EXTRAP_HABILITADA = True
    ENTRADA_2_HABILITADA = False

    # SALIDAS
    SALIDA_EXTRAP_HABILITADA = True
    SALIDA_CRUCE_4H_HABILITADA = True
    SALIDA_CONTEXTO_HABILITADA = True

    INTERFACE_VERSION = 3

    can_short = False
    timeframe = "30m"
    startup_candle_count = 120
    process_only_new_candles = True

    minimal_roi = {
        "0": 0.99
    }

    stoploss = -0.99

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    plot_config = {
        "main_plot": {
            "btc_close": {
                "color": "black",
            },
            "ema_4h": {
                "color": "red",
            },
            "ema_1d": {
                "color": "purple",
            },
            "trend_4h": {
                "color": "red",
                "dash": "dot",
            },
            "trend_1d": {
                "color": "purple",
                "dash": "dot",
            },
        }
    }

    @staticmethod
    def _rolling_trend(series, window: int):
        values = series.to_numpy(dtype=float)

        trend = np.full(len(values), np.nan)
        slope_pct = np.full(len(values), np.nan)

        x = np.arange(window, dtype=float)
        x_mean = x.mean()
        denominator = ((x - x_mean) ** 2).sum()

        for i in range(window - 1, len(values)):
            y = values[i - window + 1:i + 1]

            if np.isnan(y).any():
                continue

            y_mean = y.mean()

            slope = (
                ((x - x_mean) * (y - y_mean)).sum()
                / denominator
            )

            intercept = y_mean - slope * x_mean

            trend[i] = (
                intercept
                + slope * (window - 1)
            )

            if y[-1] != 0:
                slope_pct[i] = (
                    slope * window / y[-1]
                ) * 100

        return trend, slope_pct

    # ============================================================
    # INDICADORES
    # ============================================================

    def populate_indicators(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        # 30m:
        # 4 horas = 8 velas
        # 1 día = 48 velas

        window_4h = 8
        window_1d = 48

        dataframe["btc_close"] = dataframe["close"]

        dataframe["ema_4h"] = dataframe["close"].ewm(
            span=window_4h,
            adjust=False
        ).mean()

        dataframe["ema_1d"] = dataframe["close"].ewm(
            span=window_1d,
            adjust=False
        ).mean()

        dataframe[
            "trend_4h"
        ], dataframe[
            "slope_4h_pct"
        ] = self._rolling_trend(
            dataframe["close"],
            window_4h
        )

        dataframe[
            "trend_1d"
        ], dataframe[
            "slope_1d_pct"
        ] = self._rolling_trend(
            dataframe["close"],
            window_1d
        )

        # ========================================================
        # PENDIENTES DE DIAGNÓSTICO
        # ========================================================

        dataframe["ema_4h_slope_pct"] = (
            (
                dataframe["ema_4h"]
                / dataframe["ema_4h"].shift(2)
            ) - 1
        ) * 100

        dataframe["ema_1d_slope_pct"] = (
            (
                dataframe["ema_1d"]
                / dataframe["ema_1d"].shift(4)
            ) - 1
        ) * 100

        # ========================================================
        # CRUCES BASE
        # ========================================================

        dataframe["entry_cross"] = (
            (
                dataframe["trend_4h"]
                > dataframe["ema_4h"]
            )
            &
            (
                dataframe["trend_4h"].shift(1)
                <= dataframe["ema_4h"].shift(1)
            )
        ).astype(int)

        dataframe["exit_cross"] = (
            (
                dataframe["trend_4h"]
                < dataframe["ema_4h"]
            )
            &
            (
                dataframe["trend_4h"].shift(1)
                >= dataframe["ema_4h"].shift(1)
            )
        ).astype(int)

        # ========================================================
        # CONTEXTO EMA4H / TREND1D
        # ========================================================

        dataframe[
            "context_ema4h_above_trend1d"
        ] = (
            dataframe["ema_4h"]
            > dataframe["trend_1d"]
        ).astype(int)

        # ============================================================
        # ENTRADA 1 — EXTRAPOLACIÓN SIMPLE 1H30
        # ============================================================

        dataframe["ema_4h_step_30m"] = (
            dataframe["ema_4h"]
            - dataframe["ema_4h"].shift(1)
        )

        dataframe["trend_4h_step_30m"] = (
            dataframe["trend_4h"]
            - dataframe["trend_4h"].shift(1)
        )

        dataframe["gap_ema4h_trend4h"] = (
            dataframe["ema_4h"]
            - dataframe["trend_4h"]
        )

        dataframe["closing_power_1h30"] = (
            dataframe["trend_4h_step_30m"]
            - dataframe["ema_4h_step_30m"]
        ) * 3

        dataframe["ema_4h_proj_1h30"] = (
            dataframe["ema_4h"]
            + dataframe["ema_4h_step_30m"] * 3
        )

        dataframe["trend_4h_proj_1h30"] = (
            dataframe["trend_4h"]
            + dataframe["trend_4h_step_30m"] * 3
        )

        dataframe["pre_cross_4h_1h30"] = (
            (
                dataframe["trend_4h"]
                < dataframe["ema_4h"]
            )
            &
            (
                dataframe["gap_ema4h_trend4h"] > 0
            )
            &
            (
                dataframe["trend_4h_proj_1h30"]
                >= dataframe["ema_4h_proj_1h30"]
            )
        ).astype(int)

        # ============================================================
        # SALIDA EXTRAPOLADA SIMPLE 1H30
        # ============================================================

        dataframe["gap_trend4h_ema4h_exit"] = (
            dataframe["trend_4h"]
            - dataframe["ema_4h"]
        )

        dataframe["ema_4h_proj_exit_1h30"] = (
            dataframe["ema_4h"]
            + dataframe["ema_4h_step_30m"] * 3
        )

        dataframe["trend_4h_proj_exit_1h30"] = (
            dataframe["trend_4h"]
            + dataframe["trend_4h_step_30m"] * 3
        )

        dataframe["pre_exit_cross_4h_1h30"] = (
            (
                dataframe["trend_4h"]
                > dataframe["ema_4h"]
            )
            &
            (
                dataframe[
                    "gap_trend4h_ema4h_exit"
                ] > 0
            )
            &
            (
                dataframe["trend_4h_step_30m"]
                < dataframe["ema_4h_step_30m"]
            )
            &
            (
                dataframe[
                    "trend_4h_proj_exit_1h30"
                ]
                <= dataframe[
                    "ema_4h_proj_exit_1h30"
                ]
            )
        ).astype(int)

        # ============================================================
        # MODO 1D ALCISTA Y SEGUNDO REBOTE 4H
        # ============================================================

        dataframe["ema_1d_step_30m"] = (
            dataframe["ema_1d"]
            - dataframe["ema_1d"].shift(1)
        )

        dataframe["trend_1d_step_30m"] = (
            dataframe["trend_1d"]
            - dataframe["trend_1d"].shift(1)
        )

        dataframe[
            "modo_1d_alcista_confirmado"
        ] = (
            (
                dataframe["ema_1d"]
                > dataframe["trend_1d"]
            )
            &
            (
                dataframe["ema_1d_step_30m"] > 0
            )
            &
            (
                dataframe["trend_1d_step_30m"] >= 0
            )
        ).astype(int)

        dataframe["rebote_4h_alcista"] = (
            (
                dataframe["trend_4h"]
                > dataframe["ema_4h"]
            )
            &
            (
                dataframe["trend_4h"].shift(1)
                <= dataframe["ema_4h"].shift(1)
            )
        ).astype(int)

        # ============================================================
        # FILTRO DE VELAS PARA ENTRADA BASE
        # ============================================================

        dataframe["vela_base_rango"] = (
            dataframe["high"]
            - dataframe["low"]
        )

        dataframe["vela_base_cuerpo_abs"] = (
            dataframe["close"]
            - dataframe["open"]
        ).abs()

        dataframe["vela_base_body_pct"] = (
            dataframe["vela_base_cuerpo_abs"]
            / dataframe["open"].replace(
                0,
                np.nan
            )
            * 100
        )

        dataframe["vela_base_range_pct"] = (
            dataframe["vela_base_rango"]
            / dataframe["open"].replace(
                0,
                np.nan
            )
            * 100
        )

        dataframe[
            "vela_base_posicion_cierre"
        ] = (
            (
                dataframe["close"]
                - dataframe["low"]
            )
            / dataframe[
                "vela_base_rango"
            ].replace(
                0,
                np.nan
            )
        ).fillna(0)

        cuerpo_alto = dataframe[
            ["open", "close"]
        ].max(axis=1)

        cuerpo_bajo = dataframe[
            ["open", "close"]
        ].min(axis=1)

        dataframe[
            "vela_base_mecha_superior"
        ] = (
            dataframe["high"]
            - cuerpo_alto
        )

        dataframe[
            "vela_base_mecha_inferior"
        ] = (
            cuerpo_bajo
            - dataframe["low"]
        )

        dataframe[
            "vela_base_mecha_sup_vs_cuerpo"
        ] = (
            dataframe[
                "vela_base_mecha_superior"
            ]
            / dataframe[
                "vela_base_cuerpo_abs"
            ].replace(
                0,
                np.nan
            )
        ).replace(
            [np.inf, -np.inf],
            np.nan
        ).fillna(99)

        dataframe[
            "vela_base_mecha_inf_vs_cuerpo"
        ] = (
            dataframe[
                "vela_base_mecha_inferior"
            ]
            / dataframe[
                "vela_base_cuerpo_abs"
            ].replace(
                0,
                np.nan
            )
        ).replace(
            [np.inf, -np.inf],
            np.nan
        ).fillna(0)

        dataframe["vela_base_verde"] = (
            dataframe["close"]
            > dataframe["open"]
        ).astype(int)

        dataframe[
            "vela_base_roja_previa"
        ] = (
            dataframe["close"].shift(1)
            < dataframe["open"].shift(1)
        ).astype(int)

        # Vela alcista sana.
        dataframe[
            "vela_base_alcista_sana"
        ] = (
            (
                dataframe["vela_base_verde"] == 1
            )
            &
            (
                dataframe["vela_base_body_pct"]
                >= 0.05
            )
            &
            (
                dataframe["vela_base_body_pct"]
                <= 1.50
            )
            &
            (
                dataframe[
                    "vela_base_posicion_cierre"
                ] >= 0.60
            )
            &
            (
                dataframe[
                    "vela_base_mecha_sup_vs_cuerpo"
                ] <= 1.50
            )
        ).astype(int)

        # Envolvente alcista.
        dataframe[
            "vela_base_envolvente_alcista"
        ] = (
            (
                dataframe[
                    "vela_base_roja_previa"
                ] == 1
            )
            &
            (
                dataframe["vela_base_verde"] == 1
            )
            &
            (
                dataframe["open"]
                <= dataframe["close"].shift(1)
            )
            &
            (
                dataframe["close"]
                >= dataframe["open"].shift(1)
            )
            &
            (
                dataframe["vela_base_body_pct"]
                >= 0.07
            )
            &
            (
                dataframe[
                    "vela_base_posicion_cierre"
                ] >= 0.60
            )
        ).astype(int)

        # Rechazo bajista recuperado.
        dataframe[
            "vela_base_rechazo_bajista_recuperado"
        ] = (
            (
                dataframe["vela_base_verde"] == 1
            )
            &
            (
                dataframe["vela_base_body_pct"]
                >= 0.04
            )
            &
            (
                dataframe[
                    "vela_base_posicion_cierre"
                ] >= 0.65
            )
            &
            (
                dataframe[
                    "vela_base_mecha_inf_vs_cuerpo"
                ] >= 1.20
            )
            &
            (
                dataframe[
                    "vela_base_mecha_sup_vs_cuerpo"
                ] <= 1.50
            )
        ).astype(int)

        dataframe["vela_base_no_fomo"] = (
            (
                dataframe["vela_base_body_pct"]
                <= 1.50
            )
            &
            (
                dataframe["vela_base_range_pct"]
                <= 2.50
            )
        ).astype(int)

        dataframe["vela_base_entrada_ok"] = (
            (
                (
                    dataframe[
                        "vela_base_alcista_sana"
                    ] == 1
                )
                |
                (
                    dataframe[
                        "vela_base_envolvente_alcista"
                    ] == 1
                )
                |
                (
                    dataframe[
                        "vela_base_rechazo_bajista_recuperado"
                    ] == 1
                )
            )
            &
            (
                dataframe[
                    "vela_base_no_fomo"
                ] == 1
            )
        ).astype(int)

        # ============================================================
        # ENTRADA BASE
        # ============================================================

        dataframe["entry_setup"] = (
            (
                dataframe["entry_cross"] == 1
            )
            &
            (
                dataframe["trend_4h"]
                > dataframe["ema_4h"]
            )
            &
            (
                dataframe[
                    "context_ema4h_above_trend1d"
                ] == 1
            )
            &
            (
                dataframe[
                    "vela_base_entrada_ok"
                ] == 1
            )
        ).astype(int)

        # ============================================================
        # SALIDAS BASE
        # ============================================================

        dataframe["exit_cross_short"] = (
            (
                dataframe["exit_cross"] == 1
            )
            &
            (
                dataframe["trend_4h"]
                < dataframe["ema_4h"]
            )
        ).astype(int)

        dataframe["exit_context_lost"] = (
            (
                dataframe["ema_4h"]
                < dataframe["trend_1d"]
            )
            &
            (
                dataframe["ema_4h"].shift(1)
                >= dataframe["trend_1d"].shift(1)
            )
            &
            (
                dataframe["trend_4h"]
                < dataframe["ema_4h"]
            )
        ).astype(int)

        dataframe["exit_anticipada_1h30"] = (
            dataframe[
                "pre_exit_cross_4h_1h30"
            ] == 1
        ).astype(int)

        # Se conserva únicamente como indicador diagnóstico.
        dataframe["exit_setup"] = (
            (
                dataframe["exit_cross_short"] == 1
            )
            |
            (
                dataframe["exit_context_lost"] == 1
            )
            |
            (
                dataframe[
                    "exit_anticipada_1h30"
                ] == 1
            )
        ).astype(int)

        # ============================================================
        # ENTRADA 2 — INDICADORES DE SECUENCIA
        # ============================================================

        dataframe["ema_1d_step_30m"] = (
            dataframe["ema_1d"]
            - dataframe["ema_1d"].shift(1)
        )

        dataframe["trend_1d_step_30m"] = (
            dataframe["trend_1d"]
            - dataframe["trend_1d"].shift(1)
        )

        dataframe[
            "cross_trend4h_ema4h_alcista"
        ] = (
            (
                dataframe["trend_4h"]
                > dataframe["ema_4h"]
            )
            &
            (
                dataframe["trend_4h"].shift(1)
                <= dataframe["ema_4h"].shift(1)
            )
        ).astype(int)

        dataframe[
            "cruce_4h_alcista_reciente"
        ] = (
            dataframe[
                "cross_trend4h_ema4h_alcista"
            ]
            .rolling(
                3,
                min_periods=1
            )
            .max()
        ).fillna(0).astype(int)

        # ============================================================
        # INDICADOR ESTRUCTURAL
        # COMPRESIÓN / EXPANSIÓN
        # ============================================================

        dataframe[
            "estructura_spread_pct"
        ] = (
            (
                dataframe[
                    [
                        "ema_4h",
                        "trend_4h",
                        "ema_1d",
                        "trend_1d",
                    ]
                ].max(axis=1)
                -
                dataframe[
                    [
                        "ema_4h",
                        "trend_4h",
                        "ema_1d",
                        "trend_1d",
                    ]
                ].min(axis=1)
            )
            / dataframe["close"]
            * 100
        )

        dataframe[
            "estructura_comprimida"
        ] = (
            dataframe[
                "estructura_spread_pct"
            ] <= 0.50
        ).astype(int)

        dataframe[
            "estructura_expandiendo"
        ] = (
            dataframe[
                "estructura_spread_pct"
            ]
            > dataframe[
                "estructura_spread_pct"
            ].shift(1)
        ).astype(int)

        dataframe[
            "estructura_entrada_ok"
        ] = (
            (
                dataframe[
                    "estructura_comprimida"
                ] == 0
            )
            |
            (
                dataframe[
                    "estructura_expandiendo"
                ] == 1
            )
        ).astype(int)

        return dataframe

    # ============================================================
    # ENTRADAS
    # ============================================================

    def populate_entry_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        dataframe["enter_long"] = 0
        dataframe["enter_tag"] = ""

        # ============================================================
        # ENTRADA BASE
        # ============================================================

        if self.ENTRADA_BASE_HABILITADA:

            condicion_base = (
                dataframe["entry_setup"] == 1
            )

            dataframe.loc[
                condicion_base,
                ["enter_long", "enter_tag"]
            ] = (
                1,
                "entrada_1_3_ema4h_arriba_trend1d"
            )

        # ============================================================
        # ENTRADA 1
        # EXTRAPOLACIÓN ARMADA + CONFIRMACIÓN TREND1D
        # ============================================================

        entrada_anticipada_1h = pd.Series(
            False,
            index=dataframe.index,
            dtype=bool,
        )

        entrada_armada = False

        for i in range(1, len(dataframe)):

            ema4h_alcista = (
                dataframe[
                    "ema_4h_step_30m"
                ].iloc[i] > 0
            )

            trend4h_alcista = (
                dataframe[
                    "trend_4h_step_30m"
                ].iloc[i] > 0
            )

            trend1d_debajo = (
                dataframe[
                    "trend_1d"
                ].iloc[i]
                < dataframe[
                    "ema_4h"
                ].iloc[i]
                and
                dataframe[
                    "trend_1d"
                ].iloc[i]
                < dataframe[
                    "trend_4h"
                ].iloc[i]
            )

            extrapolacion_detectada = (
                dataframe[
                    "pre_cross_4h_1h30"
                ].iloc[i] == 1
            )

            trend1d_gira_alcista = (
                dataframe[
                    "trend_1d"
                ].iloc[i]
                >
                dataframe[
                    "trend_1d"
                ].iloc[i - 1]
            )

            # ========================================================
            # ARMADO
            # ========================================================

            if (
                not entrada_armada
                and ema4h_alcista
                and trend4h_alcista
                and trend1d_debajo
                and extrapolacion_detectada
            ):
                entrada_armada = True
                continue

            # ========================================================
            # CANCELACIÓN
            # ========================================================

            if entrada_armada and (
                not ema4h_alcista
                or not trend4h_alcista
                or not trend1d_debajo
            ):
                entrada_armada = False
                continue

            # ========================================================
            # CONFIRMACIÓN
            # ========================================================

            if (
                entrada_armada
                and trend1d_gira_alcista
                and dataframe[
                    "volume"
                ].iloc[i] > 0
            ):

                if (
                    dataframe[
                        "estructura_entrada_ok"
                    ].iloc[i] == 1
                ):
                    entrada_anticipada_1h.iloc[
                        i
                    ] = True

                entrada_armada = False

        # ============================================================
        # INTERRUPTOR ENTRADA 1
        # ============================================================

        if self.ENTRADA_1_EXTRAP_HABILITADA:

            dataframe.loc[
                entrada_anticipada_1h,
                ["enter_long", "enter_tag"]
            ] = (
                1,
                "entrada_1_3_extrapolacion_simple_1h30"
            )

        # ============================================================
        # ENTRADA 2
        # SECUENCIA REAL 4H / TREND1D / EMA1D
        # ============================================================

        entrada_alineacion_4h_1d = pd.Series(
            False,
            index=dataframe.index,
            dtype=bool,
        )

        alineacion_armada = False
        expansion_latente = False
        indice_inicio_expansion = None

        # 4 velas x 30m = 2 horas.
        ventana_expansion_velas = 4

        for i in range(1, len(dataframe)):

            cruce_4h_alcista = (
                dataframe[
                    "cross_trend4h_ema4h_alcista"
                ].iloc[i] == 1
            )

            trend4h_sobre_ema4h = (
                dataframe[
                    "trend_4h"
                ].iloc[i]
                >
                dataframe[
                    "ema_4h"
                ].iloc[i]
            )

            estructura_4h_sobre_trend1d = (
                dataframe[
                    "trend_4h"
                ].iloc[i]
                >
                dataframe[
                    "trend_1d"
                ].iloc[i]
                and
                dataframe[
                    "ema_4h"
                ].iloc[i]
                >
                dataframe[
                    "trend_1d"
                ].iloc[i]
            )

            ema1d_alcista = (
                dataframe[
                    "ema_1d_step_30m"
                ].iloc[i] > 0
            )

            # ========================================================
            # PASO 1 — ARMADO
            # ========================================================

            if cruce_4h_alcista:

                alineacion_armada = True
                expansion_latente = False
                indice_inicio_expansion = None

            if not alineacion_armada:
                continue

            # ========================================================
            # CANCELACIÓN
            # ========================================================

            if not trend4h_sobre_ema4h:

                alineacion_armada = False
                expansion_latente = False
                indice_inicio_expansion = None

                continue

            # ========================================================
            # EXPANSIÓN LATENTE
            # ========================================================

            if (
                not expansion_latente
                and estructura_4h_sobre_trend1d
                and ema1d_alcista
            ):
                expansion_latente = True
                indice_inicio_expansion = i

            if not expansion_latente:
                continue

            # ========================================================
            # CADUCIDAD
            # ========================================================

            if (
                indice_inicio_expansion is not None
                and
                i - indice_inicio_expansion
                > ventana_expansion_velas
            ):
                alineacion_armada = False
                expansion_latente = False
                indice_inicio_expansion = None

                continue

            # ========================================================
            # EXPANSIÓN REAL
            # ========================================================

            ema4h_subiendo = (
                dataframe[
                    "ema_4h_step_30m"
                ].iloc[i] > 0
            )

            trend4h_subiendo = (
                dataframe[
                    "trend_4h_step_30m"
                ].iloc[i] > 0
            )

            ema1d_subiendo = (
                dataframe[
                    "ema_1d_step_30m"
                ].iloc[i] > 0
            )

            trend1d_subiendo = (
                dataframe[
                    "trend_1d_step_30m"
                ].iloc[i] > 0
            )

            spread_expandiendo = (
                dataframe[
                    "estructura_spread_pct"
                ].iloc[i]
                >
                dataframe[
                    "estructura_spread_pct"
                ].iloc[i - 1]
            )

            expansion_confirmada = (
                estructura_4h_sobre_trend1d
                and ema4h_subiendo
                and trend4h_subiendo
                and ema1d_subiendo
                and trend1d_subiendo
                and spread_expandiendo
            )

            # ========================================================
            # INTERRUPTOR ENTRADA 2
            # ========================================================

            if (
                self.ENTRADA_2_HABILITADA
                and expansion_confirmada
                and dataframe[
                    "volume"
                ].iloc[i] > 0
                and dataframe[
                    "enter_long"
                ].iloc[i] != 1
            ):

                entrada_alineacion_4h_1d.iloc[
                    i
                ] = True

                alineacion_armada = False
                expansion_latente = False
                indice_inicio_expansion = None

        dataframe.loc[
            entrada_alineacion_4h_1d,
            ["enter_long", "enter_tag"]
        ] = (
            1,
            "entrada_1_3_alineacion_4h_1d_proyectada_1h30"
        )

        return dataframe

    # ============================================================
    # CONFIRMACIÓN DE SALIDAS
    # ============================================================

    def confirm_trade_exit(
        self,
        pair: str,
        trade,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        exit_reason: str,
        current_time,
        **kwargs,
    ) -> bool:

        # ========================================================
        # SALIDAS DE SEGURIDAD
        # Nunca se bloquean por los interruptores experimentales.
        # ========================================================

        salidas_no_bloqueables = {
            "stop_loss",
            "stoploss",
            "trailing_stop_loss",
            "force_exit",
            "emergency_exit",
            "liquidation",
        }

        if exit_reason in salidas_no_bloqueables:
            return True

        salida_anticipada = (
            "salida_1_3_extrapolacion_simple_1h30"
        )

        salida_cruce_real = (
            "salida_1_3_cruce_4h_real"
        )

        salida_contexto = (
            "salida_1_3_contexto_perdido"
        )

        salidas_que_esperan_segundo_rebote = {
            salida_anticipada,
            salida_cruce_real,
        }

        salidas_controladas = {
            salida_anticipada,
            salida_cruce_real,
            salida_contexto,
        }

        if exit_reason not in salidas_controladas:
            return True

        if not self.dp:
            return True

        dataframe, _ = (
            self.dp.get_analyzed_dataframe(
                pair,
                self.timeframe
            )
        )

        if dataframe is None or dataframe.empty:
            return True

        fechas = pd.to_datetime(
            dataframe["date"],
            utc=True
        )

        tiempo_actual = pd.to_datetime(
            current_time,
            utc=True
        )

        entrada_trade = pd.to_datetime(
            trade.open_date_utc,
            utc=True
        )

        fila_actual = dataframe.loc[
            fechas <= tiempo_actual
        ].tail(1)

        if fila_actual.empty:
            return True

        fila = fila_actual.iloc[-1]

        modo_1d_alcista = int(
            fila.get(
                "modo_1d_alcista_confirmado",
                0
            )
        ) == 1

        tramo_trade = dataframe.loc[
            (fechas >= entrada_trade)
            &
            (fechas <= tiempo_actual)
        ]

        if tramo_trade.empty:
            return True

        rebotes_desde_entrada = int(
            tramo_trade[
                "rebote_4h_alcista"
            ].fillna(0).sum()
        )

        # ========================================================
        # REGLA 1
        #
        # Salida EXTRAP y Cruce real esperan
        # el segundo rebote.
        # ========================================================

        if (
            exit_reason
            in salidas_que_esperan_segundo_rebote
            and rebotes_desde_entrada < 2
        ):
            return False

        # ========================================================
        # REGLA 2
        #
        # Contexto perdido sólo se bloquea si
        # el modo 1D continúa alcista.
        # ========================================================

        if (
            exit_reason == salida_contexto
            and modo_1d_alcista
            and rebotes_desde_entrada < 2
        ):
            return False

        return True

    # ============================================================
    # SALIDAS
    # ============================================================

    def populate_exit_trend(
        self,
        dataframe: DataFrame,
        metadata: dict
    ) -> DataFrame:

        dataframe["exit_long"] = 0
        dataframe["exit_tag"] = ""

        # ========================================================
        # SALIDA 1 — CRUCE 4H REAL
        # ========================================================

        if self.SALIDA_CRUCE_4H_HABILITADA:

            condicion_cruce = (
                dataframe[
                    "exit_cross_short"
                ] == 1
            )

            dataframe.loc[
                condicion_cruce,
                "exit_long"
            ] = 1

            dataframe.loc[
                condicion_cruce,
                "exit_tag"
            ] = (
                "salida_1_3_cruce_4h_real"
            )

        # ========================================================
        # SALIDA 2 — CONTEXTO PERDIDO
        # ========================================================

        if self.SALIDA_CONTEXTO_HABILITADA:

            condicion_contexto = (
                dataframe[
                    "exit_context_lost"
                ] == 1
            )

            dataframe.loc[
                condicion_contexto,
                "exit_long"
            ] = 1

            dataframe.loc[
                condicion_contexto,
                "exit_tag"
            ] = (
                "salida_1_3_contexto_perdido"
            )

        # ========================================================
        # SALIDA 3 — EXTRAPOLACIÓN SIMPLE 1H30
        # ========================================================

        if self.SALIDA_EXTRAP_HABILITADA:

            condicion_extrap = (
                dataframe[
                    "exit_anticipada_1h30"
                ] == 1
            )

            dataframe.loc[
                condicion_extrap,
                "exit_long"
            ] = 1

            dataframe.loc[
                condicion_extrap,
                "exit_tag"
            ] = (
                "salida_1_3_extrapolacion_simple_1h30"
            )
        return dataframe