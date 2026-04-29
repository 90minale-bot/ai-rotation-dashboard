# 📊 AI vs Value Rotation Dashboard

A real-time market regime dashboard that tracks whether market leadership is favoring **AI/growth** or rotating toward **value, cyclicals, quality, and defensive assets**.

🔗 **Live App:**  
https://ai-rotation-dashboard-n4zfvvuuqztpxk6rngqp5t.streamlit.app/

---



# 🚀 Overview

This project analyzes cross-asset signals to identify **market rotation trends**:

- AI / Growth dominance
- Early rotation signals
- Confirmed rotation into value/defensive assets
- Risk appetite vs risk-off behavior

It is designed as a **decision-support tool**, not a prediction engine.

---

# 🧠 Core Concept

Markets rotate between:

### 🔵 AI / Growth Leadership
- Driven by innovation, liquidity, and momentum
- Concentrated in mega-cap tech and semiconductors

### 🟠 Value / Cyclical Rotation
- Driven by economic expansion, inflation, or mean reversion
- Broader participation across sectors

This dashboard quantifies that shift using **relative performance ratios + trend signals**.

---

# 📈 Signals & Methodology

The model evaluates 9 key signals:

### Value vs AI
- `VTV / QQQ` → Value vs Growth

### Cyclicals
- `XLI / QQQ` → Industrials vs AI
- `XLE / QQQ` → Energy vs AI

### International
- `EFV / QQQ` → International Value vs AI
- `VEA / QQQ` → Developed Markets vs AI

### Quality & Breadth
- `QUAL / ARKK` → Quality vs Speculation
- `RSP / SPY` → Market Breadth

### Credit & Risk
- `JNK / IEF` → Risk Appetite (credit spreads)
- `TLT trend` → Bonds (defensive signal)
- `VIX trend` → Volatility

Each signal contributes to a **Rotation Score (0–9)**.

---

# 📊 Rotation Score Interpretation

| Score | Regime |
|------|--------|
| 0–2  | AI / Growth Dominance |
| 3–4  | Early Rotation |
| 5–6  | Confirmed Rotation |
| 7–9  | Strong Value / Defensive Rotation |

---

# 📉 Trend Signal

The dashboard also calculates a **trend over time**:

- `AI ↑↑` → AI dominance strengthening  
- `ROT ↑` → Rotation improving  
- `ROT ↑↑` → Rotation strengthening  
- `ROT ↓` → Rotation weakening  

This provides **early warning signals before full rotation occurs**.

---

# 🎯 Recommendation Layer

The app translates signals into **portfolio bias guidance**:

- Aggressive growth (AI-driven)
- Balanced / transition
- Value / quality tilt
- Defensive positioning


---

# 🖥️ Features

- 📊 Interactive charts (Plotly + Streamlit)
- 🔄 Real-time rotation tracking
- 📉 Momentum + trend indicators
- 🧠 Regime interpretation
- 📌 Portfolio bias recommendations
- 📱 Web-accessible dashboard

---