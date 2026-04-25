AI Agent Specification – Defense Sector Stock Analytics

PURPOSE

This project implements a sector-aware machine learning prediction system for defense-sector equities.

The AI agent’s role is to:

Train sector-aware prediction models

Generate next-day return forecasts

Produce trading regime signals (LONG / FLAT / SHORT)

Quantify signal strength

Evaluate predictive performance

Assist in model improvement and feature engineering

The system operates fully locally.

PRIMARY OBJECTIVE

Predict:

target_next_ret_1

Definition:

Close-to-close next-day return

All signals and strength metrics are derived from this target.

DOMAIN CONTEXT

Sector Focus:

U.S. Defense / Aerospace equities

Sector Proxy:

ITA (iShares U.S. Aerospace & Defense ETF)

Core assumption:

Defense stocks exhibit correlated sector movement and relative leadership behavior.

The agent must account for:

Stock-level technical structure

Sector behavior

Relative strength

AGENT RESPONSIBILITIES
1️⃣ Model Training

File:

main.py

Responsibilities:

Pull stock + ITA data

Build consistent feature set

Train Ridge regression model

Use time-series cross validation

Save model artifact with feature list

Artifact structure:

{
  "model": sklearn pipeline,
  "features": [feature list],
  "target": "target_next_ret_1",
  "meta": training info
}
2️⃣ Prediction Engine

File:

Dashboard/dashboard.py

Responsibilities:

Load trained model

Rebuild identical feature set

Generate next-day prediction

Output:

Predicted next-day return

Implied next-day close

LONG / FLAT / SHORT signal

Signal logic:

LONG  if pred > +threshold
SHORT if pred < -threshold (if enabled)
FLAT  otherwise
3️⃣ Signal Strength Engine

Definition:

Signal strength = percentile rank of today’s prediction relative to last 90 predictions.

Scale:

0–20 → Strong bearish

40–60 → Neutral

80–100 → Strong bullish

Purpose:

Measure extremeness of signal

Separate weak drift from high-conviction regimes

Improve exposure control

Agent must ensure:

Strength is computed from expanding or rolling window

Distribution is stable

Strength reflects magnitude + direction

4️⃣ Strategy Evaluation

Dashboard evaluates:

Directional accuracy

MAE

RMSE

Days in market

Long / Short distribution

Cumulative performance vs Buy & Hold

Agent must:

Avoid lookahead bias

Use only information available at prediction time

Ensure correct date alignment

5️⃣ Strength Validation Script

File:

strength_vs_actual.py

Responsibilities:

Compare strength percentile vs next-day actual returns

Output:

Correlation(strength, actual)

Bucket analysis (0–20, 20–40, etc.)

Top strength days

CSV export

Purpose:

Validate whether stronger signals correspond to better next-day outcomes.

FEATURE ARCHITECTURE

Feature Categories:

Stock Technical Features

Sector (ITA) Features

Relative Strength Features

All feature engineering must remain consistent across:

Training

Dashboard

Analysis scripts

Feature drift is not permitted.

MODELING CONSTRAINTS

Time-series split only (no random shuffle)

No future data leakage

Rolling statistics must use past-only data

No target leakage

Consistent timezone normalization

SIGNAL PHILOSOPHY

This is a short-horizon drift model, not a price target model.

Interpretation guidelines:

Small positive predictions matter

Extreme predictions are rare

Signal strength measures relative extremeness

Model captures bias, not macro shocks

TRADING REGIME LOGIC

Agent must support:

Long / Flat

Long / Flat / Short

Threshold slider controls strictness.

Recommended defaults:

Threshold: 0.00–0.10%

Mode: Long / Flat

EVALUATION FRAMEWORK

Agent should prioritize:

Stability over overfitting

Sector-awareness over single-stock modeling

Relative strength as signal amplifier

Drift capture vs volatility chasing

FUTURE EXTENSIONS

Agent may expand into:

Multi-stock ranking engine

Cross-sectional defense basket model

Position sizing logic (scaled by signal strength)

Rolling regime detection

Macro overlay integration

News sentiment integration

Portfolio-level risk control

RISK DISCLOSURE

This system:

Is experimental

Is not financial advice

Predicts short-term statistical bias

Does not account for transaction costs or slippage

Does not model intraday execution risk

DESIGN PRINCIPLES

Transparency

Reproducibility

Deterministic feature construction

Explicit signal logic

No hidden heuristics

AGENT SUCCESS METRICS

The agent is considered successful if:

Model predictions are reproducible

Feature consistency is maintained

Signal strength correlates positively with next-day performance

Strategy performance exceeds buy-and-hold over evaluation window

No data leakage is introduced

LONG TERM AGENT ROLE

Evolve into:

A sector-aware quantitative assistant capable of detecting regime shifts, ranking opportunities, and providing disciplined exposure guidance for defense equities.