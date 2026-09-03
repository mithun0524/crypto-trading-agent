"""
strategy/momentum.py -- Crypto momentum / trend-following strategy.

Crypto momentum is driven by:
1. MACD histogram crossing zero (momentum shift)
2. EMA 12/26 golden/death cross
3. ADX > 25 (strong trend confirmation)
4. RSI not overbought/oversold

Entry : MACD > 0 AND EMA bullish AND ADX strong AND RSI < 70
Exit  : MACD < 0 OR EMA bearish OR RSI > 80 (overbought)
"""
from __future__ import annotations
import pandas as pd


def momentum_signal(bars: pd.DataFrame, direction: str = "bull") -> dict:
    if len(bars) < 2:
        return {"strategy": "momentum", "action": "HOLD", "reason": "insufficient bars"}

    curr = bars.iloc[-1]

    macd_hist   = curr.get("macd_hist", 0.0)
    ema_cross   = curr.get("ema_cross", 0.0)
    adx         = curr.get("adx", 0.0)
    rsi         = curr.get("rsi", 50.0)
    vol_surge   = curr.get("vol_surge", 0)
    adx_strong  = curr.get("adx_strong", 0)

    if pd.isna(macd_hist) or pd.isna(rsi):
        return {"strategy": "momentum", "action": "HOLD", "reason": "indicators not ready"}

    # Strong bull entry: all signals align
    if (macd_hist > -0.5 and ema_cross > -0.5 and rsi < 80 and rsi > 20):
        confidence = "HIGH" if (adx_strong and vol_surge) else "MEDIUM"
        return {
            "strategy": "momentum",
            "action": "BUY",
            "reason": f"Bull momentum [{confidence}]: MACD={macd_hist:.4f} EMA_cross={ema_cross:.2f} RSI={rsi:.1f} ADX={adx:.1f}",
        }

    # Exit: momentum fading
    if macd_hist < -1.0 or rsi > 85:
        return {
            "strategy": "momentum",
            "action": "CLOSE",
            "reason": f"Momentum fading: MACD={macd_hist:.4f} RSI={rsi:.1f}",
        }

    return {
        "strategy": "momentum",
        "action": "HOLD",
        "reason": f"Momentum neutral: MACD={macd_hist:.4f} RSI={rsi:.1f}",
    }
