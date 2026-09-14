# BTC Strategy Lab

A public research laboratory for experimental **Freqtrade strategies focused on BTC/USDT**.

This repository is intended for developers, quantitative traders and researchers who want to inspect, test, modify and challenge different trading ideas.

The goal is not to publish a “winning bot”.

The goal is to create a practical exchange of ideas around trading logic, market behavior and strategy design.

## What you will find here

The repository currently contains two groups:

### Original strategies

`strategies/BTC/originals/`

A collection of independent strategy concepts using different technical approaches such as:

- momentum
- mean reversion
- volatility expansion
- trend following
- volume and money flow
- Fisher Transform
- Bollinger Bands
- ADX / EMA structures
- CCI
- Chaikin Money Flow

These files are intended to serve as starting points for testing and experimentation.

### Experimental improvements

`strategies/BTC/improvements/`

Selected examples showing how an original strategy can be modified after analyzing its behavior.

These are **research candidates**, not final strategies.

The complete internal research path and our strongest private variants are not published.

## Current public set

At launch the repository contains:

- 10 original BTC strategy concepts
- 2 selected experimental improvements

More strategies may be added gradually.

## How to use

The strategies are written for Freqtrade.

A typical workflow is:

1. Review the strategy code.
2. Copy the `.py` file into your Freqtrade `user_data/strategies/` directory.
3. Test it using your own configuration, exchange data and trading assumptions.
4. Perform your own backtests and validation.
5. Modify the strategy if you find an interesting hypothesis.

Do not assume that our environment, fees, market period or execution conditions match yours.

## We want independent results

If you test one of these strategies, useful feedback is welcome.

Especially interesting contributions include:

- bugs
- unexpected behavior
- alternative filters
- entry or exit observations
- regime sensitivity
- drawdown behavior
- failed hypotheses
- successful modifications
- out-of-sample tests
- walk-forward tests
- comparisons across different market periods

A negative result is also useful if it is reproducible.

When sharing a test, please include whenever possible:

- strategy name
- Freqtrade version
- trading pair
- timeframe
- test period
- fees
- relevant configuration
- number of trades
- basic performance statistics
- modification made, if any

The objective is to exchange **evidence**, not screenshots of isolated profits.

## Research philosophy

A trading strategy rarely improves because of a single indicator or parameter.

Small observations about entries, exits, volatility, volume, market regime or loss behavior can become useful pieces of information.

This repository is therefore treated as a laboratory rather than a catalogue of finished products.

If you find something interesting, open an Issue and share it.

## Important limitations

These strategies are experimental.

They may:

- lose money;
- perform differently across market regimes;
- suffer significant drawdowns;
- behave differently with other exchanges or fees;
- be overfit to a historical period;
- stop working in future market conditions.

Historical backtests do not guarantee future performance.

Independent validation is strongly recommended before considering any real-world use.

## Disclaimer

This repository is provided for educational and research purposes only.

Nothing contained here constitutes financial or investment advice.

Use of the code and any trading decisions remain entirely the responsibility of the user.

---

### Want to contribute?

Test a strategy, challenge an assumption, report a bug or propose an improvement.

Useful criticism is more valuable here than agreement.
