"""
Crypto Snapshot Pro — Bankr Agent (БЕЗ X402 ЛОГИКИ)
Bankr сам обрабатывает платежи
Вывод в чистом Markdown для терминала
"""

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
import time
import json
import logging
import sys
import os
from dotenv import load_dotenv

# ============================================================
# ЗАГРУЗКА ПЕРЕМЕННЫХ И ЛОГГЕР
# ============================================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("crypto-snapshot")

# ============================================================
# ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# ============================================================

# ПРОКСИ
USE_PROXY = os.getenv("PROXY_ENABLED", "false").lower() == "true"
PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = os.getenv("PROXY_PORT")
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")

if USE_PROXY and PROXY_HOST and PROXY_PORT and PROXY_USER and PROXY_PASS:
    PROXY_URL = f"socks5://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"
    logger.info(f"✅ Proxy enabled: {PROXY_HOST}:{PROXY_PORT}")
else:
    PROXY_URL = None
    logger.info("ℹ️ Proxy disabled")

BINANCE_API = "https://api.binance.com/api/v3"
_cache = {}
_CACHE_TTL = 60

# ============================================================
# СОЗДАЕМ ПРИЛОЖЕНИЕ
# ============================================================

app = FastAPI(
    title="Crypto Snapshot Pro (Bankr)"
)

# ============================================================
# MCP СЕРВЕР
# ============================================================

from fastapi import FastAPI as _FastAPI

mcp_app = _FastAPI(title="MCP Server")

@mcp_app.post("/")
async def mcp_handler(request: Request):
    try:
        body = await request.json()
        method = body.get("method", "")
        params = body.get("params", {})
        request_id = body.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    "serverInfo": {"name": "Crypto Snapshot Pro", "version": "1.0.0"}
                }
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "crypto_snapshot",
                            "description": "Get AI-powered crypto market analysis for any cryptocurrency. Returns LONG/SHORT/HOLD signal with entry, target, stop levels.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "symbol": {
                                        "type": "string",
                                        "description": "Cryptocurrency symbol (BTC, ETH, SOL, DOGE, XRP, etc.)"
                                    }
                                },
                                "required": ["symbol"]
                            }
                        }
                    ]
                }
            }

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "crypto_snapshot":
                symbol = arguments.get("symbol", "BTC")

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        "http://localhost:10000/",
                        json={"symbol": symbol}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        # Извлекаем analysis из ответа
                        content = data.get("analysis", str(data))
                        return {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "content": [{"type": "text", "text": content}]
                            }
                        }
                    else:
                        return {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": response.status_code,
                                "message": "API error"
                            }
                        }

        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"status": "pong"}}

        if method == "notifications/initialized":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"status": "ok"}}

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found"}
        }

    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": body.get("id", 1) if 'body' in locals() else 1,
            "error": {"code": -32000, "message": str(e)}
        }

@mcp_app.get("/health")
async def mcp_health():
    return {"status": "ok", "service": "MCP Server", "version": "1.0.0"}

app.mount("/mcp", mcp_app)
logger.info("✅ MCP server mounted at /mcp")

# ============================================================
# ГЛАВНАЯ СТРАНИЦА С РАЗВЕРНУТЫМ ОПИСАНИЕМ
# ============================================================

@app.get("/")
async def root():
    return JSONResponse({
        "service": "Crypto Snapshot Pro",
        "status": "active",
        "description": "AI-powered crypto trading signals with professional technical analysis. Provides LONG/SHORT/HOLD signals with entry levels, target prices, stop-loss, and AI-generated market commentary based on RSI, MACD, Bollinger Bands, volume analysis, and pivot points. Includes conviction scoring, risk/reward ratios, and 24-hour price predictions.",
        "version": "1.0.0",
        "endpoints": {
            "POST /": "Get crypto signal (send JSON with symbol)",
            "GET /health": "Health check",
            "GET /mcp": "MCP server for AI agents"
        },
        "schema": {
            "input": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Cryptocurrency symbol (e.g., BTC, ETH, SOL, DOGE, XRP, ADA, DOT, LINK, AVAX, MATIC)",
                        "example": "BTC",
                        "pattern": "^[A-Z]+$"
                    }
                },
                "required": ["symbol"]
            },
            "output": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Trading pair symbol (e.g., BTCUSDT)"
                    },
                    "analysis": {
                        "type": "string",
                        "description": "Complete trading analysis in Markdown format with: technical signal (LONG/SHORT/HOLD), conviction level (VERY HIGH/HIGH/MEDIUM/LOW), entry/target/stop levels, RSI, EMA, MACD, Bollinger Bands, volume ratio, AI professional commentary with market assessment, price prediction, risk assessment, confidence level, key levels to watch"
                    }
                }
            }
        },
        "example": {
            "request": {"symbol": "BTC"},
            "response": {
                "symbol": "BTC",
                "analysis": "# 📊 CRYPTO SNAPSHOT PRO — BTC/USDT\n\n## 🎯 TECHNICAL SIGNAL\n**🚀 Strong Bullish Setup**\n- **Conviction:** HIGH\n- **Score:** 4.5 🟢 LONG / 1.5 🔴 SHORT\n\n---\n\n## 📈 TECHNICAL INDICATORS\n| Indicator | Value |\n|-----------|-------|\n| **Price** | $65,432.10 |\n| **24h Change** | +2.35% |\n| **RSI(14)** | 62.4 (neutral) |\n| **EMA(20)** | $64,800.00 |\n| **EMA(50)** | $63,200.00 |\n| **Volume Ratio** | 1.85x |\n\n---\n\n## 🎯 STRATEGY LEVELS\n| Level | Price |\n|-------|-------|\n| **Entry** | $65,100.00 |\n| **Target** | $66,800.00 |\n| **Stop Loss** | $64,200.00 |\n| **Risk/Reward** | 1:2.13 |\n\n---\n\n## 🤖 PROFESSIONAL AI ANALYSIS\n[AI-generated market commentary with price prediction, risk assessment, and final recommendation]\n\n---\n\n## 📌 KEY LEVELS\n| Level | Price |\n|-------|-------|\n| **Support** | $64,200.00 |\n| **Resistance** | $66,800.00 |\n| **24h High** | $66,200.00 |\n| **24h Low** | $63,800.00 |\n\n---\n\n⚠️ **Risk Disclosure:** This is NOT financial advice. Always manage risk."
            }
        }
    })

# ============================================================
# ASI ФУНКЦИИ
# ============================================================

ASI_API_KEY = os.getenv("ASI_API_KEY", "")
ASI_MODELS = [
    {"id": "asi1", "name": "ASI1"},
    {"id": "asi1-mini", "name": "ASI1 Mini"}
]

PROFESSIONAL_PROMPT = """
You are a professional crypto trader with 20+ years of experience managing institutional portfolios.
You provide conservative, data-driven trading advice with clear risk management.

Based on the technical analysis below, provide a professional trading recommendation:

TECHNICAL DATA:
Symbol: {symbol}
Current Price: ${price}
24h Change: {change}%
RSI(14): {rsi}
EMA(20): ${ema20}
EMA(50): ${ema50}
Volume Ratio: {volume_ratio}x
Signal: {signal}
Conviction: {conviction}
Entry: ${entry}
Target: ${target}
Stop: ${stop}
Risk/Reward: 1:{risk_reward}
Support: ${support}
Resistance: ${resistance}
24h High: ${high_24h}
24h Low: ${low_24h}
Long Score: {long_score}
Short Score: {short_score}

YOUR ANALYSIS MUST INCLUDE:
1. MARKET ASSESSMENT (2-3 sentences)
2. TRADE RECOMMENDATION: LONG / SHORT / HOLD
3. PRICE PREDICTION 24H with percentage
4. ENTRY ZONE
5. TARGET LEVELS T1 and T2
6. STOP LOSS with rationale
7. RISK ASSESSMENT Low/Medium/High
8. CONFIDENCE LEVEL percentage
9. KEY LEVELS TO WATCH
10. FINAL RECOMMENDATION one clear sentence

IMPORTANT RULES:
- Be CONSERVATIVE
- If indicators are mixed, recommend HOLD
- Always include specific price levels
- Professional tone, no hype
"""

def generate_fallback_analysis(signal_data: dict) -> str:
    signal = signal_data.get('signal', 'HOLD')
    rsi = signal_data.get('rsi', 50)
    entry = signal_data.get('entry', 0)
    target = signal_data.get('target', 0)
    stop = signal_data.get('stop', 0)
    support = signal_data.get('support', 0)
    resistance = signal_data.get('resistance', 0)
    
    lines = []
    if signal == "LONG":
        lines.append("📊 BULLISH SETUP DETECTED")
        lines.append(f"Price showing strength with RSI at {rsi:.1f}.")
    elif signal == "SHORT":
        lines.append("📊 BEARISH SETUP DETECTED")
        lines.append(f"Price showing weakness with RSI at {rsi:.1f}.")
    else:
        lines.append("📊 NEUTRAL MARKET")
        lines.append(f"RSI at {rsi:.1f} indicates consolidation.")
    
    lines.append(f"Entry: ${entry:.2f}, Target: ${target:.2f}, Stop: ${stop:.2f}")
    lines.append(f"Support: ${support:.2f}, Resistance: ${resistance:.2f}")
    lines.append("\n⚠️ Risk Disclosure: This is NOT financial advice.")
    return "\n".join(lines)

async def generate_ai_analysis(symbol: str, signal_data: dict) -> str:
    prompt = PROFESSIONAL_PROMPT.format(
        symbol=symbol.replace('USDT', '/USDT'),
        price=signal_data.get('price', 0),
        change=signal_data.get('change', 0),
        rsi=signal_data.get('rsi', 50),
        ema20=signal_data.get('ema20', 0),
        ema50=signal_data.get('ema50', 0),
        volume_ratio=signal_data.get('volume_ratio', 1.0),
        signal=signal_data.get('signal', 'HOLD'),
        conviction=signal_data.get('conviction', 'MEDIUM'),
        entry=signal_data.get('entry', 0),
        target=signal_data.get('target', 0),
        stop=signal_data.get('stop', 0),
        risk_reward=signal_data.get('risk_reward', 0),
        support=signal_data.get('support', 0),
        resistance=signal_data.get('resistance', 0),
        high_24h=signal_data.get('high_24h', 0),
        low_24h=signal_data.get('low_24h', 0),
        long_score=signal_data.get('long_score', 0),
        short_score=signal_data.get('short_score', 0)
    )

    if not ASI_API_KEY:
        return generate_fallback_analysis(signal_data)

    for model in ASI_MODELS:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.asi1.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {ASI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model["id"],
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a professional crypto trader with 20+ years of experience. Provide conservative, actionable advice."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.4,
                        "max_tokens": 800,
                        "top_p": 0.9
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"ASI error: {e}")
            continue

    return generate_fallback_analysis(signal_data)

# ============================================================
# ОСНОВНОЙ ОБРАБОТЧИК (БЕЗ ПЛАТЕЖЕЙ)
# ============================================================

@app.post("/")
async def crypto_snapshot(request: Request):
    """POST — генерирует сигнал (Bankr обрабатывает платежи)"""
    
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    symbol = body.get("symbol", "").strip()
    
    if not symbol:
        return JSONResponse({
            "error": "Symbol required",
            "example": {"symbol": "BTC"}
        })
    
    logger.info(f"📊 Generating signal for: {symbol}")
    result = await generate_signal(symbol)
    return JSONResponse({
        "symbol": symbol,
        "analysis": result
    })

# ============================================================
# ГЕНЕРАЦИЯ СИГНАЛА (ЧИСТЫЙ MARKDOWN)
# ============================================================

async def generate_signal(symbol: str) -> str:
    try:
        symbol = symbol.upper().replace("USDT", "").replace("USD", "")
        symbol = f"{symbol}USDT"

        ticker = await fetch_ticker(symbol)
        current_price = float(ticker.get("price", 0))
        change_24h = float(ticker.get("change", 0))
        high_24h = float(ticker.get("high", 0))
        low_24h = float(ticker.get("low", 0))

        if current_price == 0:
            raise HTTPException(status_code=503, detail="Market data unavailable")

        klines = await fetch_klines(symbol)
        closes = [k["close"] for k in klines]
        volumes = [k["volume"] for k in klines]

        rsi = calculate_rsi(closes, 14)
        ema20 = calculate_ema(closes[-20:], 20) if len(closes) >= 20 else closes[-1]
        ema50 = calculate_ema(closes[-50:], 50) if len(closes) >= 50 else closes[-1]
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else volumes[-1]
        current_volume = volumes[-1] if volumes else 0
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        high_low_range = (high_24h - low_24h) / low_24h if low_24h > 0 else 0

        macd, macd_signal, macd_hist = calculate_macd(closes)
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes)
        rsi_divergence = detect_rsi_divergence(rsi, closes)
        pivot = calculate_pivot_points(high_24h, low_24h, current_price)

        signal, signal_desc, long_score, short_score = get_signal_from_factors(
            rsi, ema20, ema50, volume_ratio, high_low_range,
            macd, macd_signal, macd_hist, bb_upper, bb_middle, bb_lower,
            rsi_divergence, pivot
        )

        atr_proxy = high_low_range * current_price
        support = low_24h
        resistance = high_24h

        if signal == "LONG":
            entry = support + (resistance - support) * 0.2
            target = entry + (entry - support) * 2
            stop = support - atr_proxy * 0.5
            risk_reward = (target - entry) / (entry - stop) if entry > stop else 0
        elif signal == "SHORT":
            entry = resistance - (resistance - support) * 0.2
            target = entry - (resistance - entry) * 2
            stop = resistance + atr_proxy * 0.5
            risk_reward = (entry - target) / (stop - entry) if stop > entry else 0
        else:
            entry = current_price
            target = current_price * 1.05
            stop = current_price * 0.95
            risk_reward = 1.0

        total_score = long_score + short_score
        conviction = "VERY HIGH" if total_score >= 5 else "HIGH" if total_score >= 4 else "MEDIUM" if total_score >= 3 else "LOW"
        rsi_status = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"

        signal_data = {
            'price': current_price,
            'change': change_24h,
            'rsi': rsi,
            'ema20': ema20,
            'ema50': ema50,
            'volume_ratio': volume_ratio,
            'signal': signal,
            'conviction': conviction,
            'entry': entry,
            'target': target,
            'stop': stop,
            'risk_reward': risk_reward,
            'support': support,
            'resistance': resistance,
            'high_24h': high_24h,
            'low_24h': low_24h,
            'long_score': long_score,
            'short_score': short_score
        }

        ai_analysis = await generate_ai_analysis(symbol, signal_data)

        # ============================================================
        # ЧИСТЫЙ MARKDOWN ВЫВОД (БЕЗ МУСОРНЫХ СИМВОЛОВ)
        # ============================================================
        
        signal_emoji = "🚀" if signal == "LONG" else "🔥" if signal == "SHORT" else "➡️"
        
        # Очищаем AI анализ от лишних символов, если они есть
        ai_analysis = ai_analysis.replace('\r', '').strip()
        
        result = f"""# 📊 CRYPTO SNAPSHOT PRO — {symbol.replace('USDT', '/USDT')}

## 🎯 TECHNICAL SIGNAL
**{signal_emoji} {signal_desc}**
- **Conviction:** {conviction}
- **Score:** {long_score:.1f} 🟢 LONG / {short_score:.1f} 🔴 SHORT

---

## 📈 TECHNICAL INDICATORS
| Indicator | Value |
|-----------|-------|
| **Price** | {format_price(current_price)} |
| **24h Change** | {change_24h:+.2f}% |
| **RSI(14)** | {rsi:.1f} ({rsi_status}) |
| **EMA(20)** | {format_price(ema20)} |
| **EMA(50)** | {format_price(ema50)} |
| **Volume Ratio** | {volume_ratio:.2f}x |

---

## 🎯 STRATEGY LEVELS
| Level | Price |
|-------|-------|
| **Entry** | {format_price(entry)} |
| **Target** | {format_price(target)} |
| **Stop Loss** | {format_price(stop)} |
| **Risk/Reward** | 1:{risk_reward:.2f} |

---

## 🤖 PROFESSIONAL AI ANALYSIS
{ai_analysis}

---

## 📌 KEY LEVELS
| Level | Price |
|-------|-------|
| **Support** | {format_price(support)} |
| **Resistance** | {format_price(resistance)} |
| **24h High** | {format_price(high_24h)} |
| **24h Low** | {format_price(low_24h)} |

---

⚠️ **Risk Disclosure:** This is NOT financial advice. Always manage risk.
"""
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

async def fetch_binance(endpoint: str, params: dict = None) -> dict:
    cache_key = f"{endpoint}_{str(params)}"
    now = time.time()

    if cache_key in _cache and now - _cache[cache_key]["time"] < _CACHE_TTL:
        return _cache[cache_key]["data"]

    try:
        if USE_PROXY and PROXY_URL:
            async with httpx.AsyncClient(timeout=15.0, proxy=PROXY_URL) as client:
                response = await client.get(f"{BINANCE_API}/{endpoint}", params=params)
        else:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(f"{BINANCE_API}/{endpoint}", params=params)

        if response.status_code != 200:
            logger.error(f"Binance error: {response.status_code}")
            raise HTTPException(status_code=503, detail="Market data unavailable")

        data = response.json()
        _cache[cache_key] = {"data": data, "time": now}
        return data

    except Exception as e:
        logger.error(f"Request error: {e}")
        raise HTTPException(status_code=503, detail="Market data unavailable")

async def fetch_ticker(symbol: str) -> dict:
    cache_key = f"ticker_{symbol}"
    now = time.time()
    if cache_key in _cache and now - _cache[cache_key]["time"] < _CACHE_TTL:
        return _cache[cache_key]["data"]

    data = await fetch_binance("ticker/24hr", {"symbol": symbol})
    price = float(data.get("lastPrice", 0))
    if price == 0:
        raise HTTPException(status_code=503, detail="Invalid price data")

    result = {
        "price": price,
        "change": float(data.get("priceChangePercent", 0)),
        "high": float(data.get("highPrice", 0)),
        "low": float(data.get("lowPrice", 0)),
        "volume": float(data.get("volume", 0)),
        "time": time.time()
    }
    _cache[cache_key] = {"data": result, "time": now}
    return result

async def fetch_klines(symbol: str, interval: str = "1d", limit: int = 50) -> list[dict]:
    cache_key = f"klines_{symbol}_{interval}_{limit}"
    now = time.time()
    if cache_key in _cache and now - _cache[cache_key]["time"] < _CACHE_TTL:
        return _cache[cache_key]["data"]

    data = await fetch_binance("klines", {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    })

    if not data or len(data) < 5:
        raise HTTPException(status_code=503, detail="Insufficient historical data")

    klines = [{'close': float(c[4]), 'high': float(c[2]), 'low': float(c[3]), 'volume': float(c[5]), 'time': int(c[0])} for c in data]
    _cache[cache_key] = {"data": klines, "time": now}
    return klines

def calculate_rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(diff if diff >= 0 else 0)
        losses.append(0 if diff >= 0 else abs(diff))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 1)

def calculate_ema(prices: list[float], period: int) -> float:
    if not prices:
        return 0.0
    multiplier = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = (price - ema) * multiplier + ema
    return round(ema, 2)

def calculate_macd(closes: list[float]) -> tuple[float, float, float]:
    if len(closes) < 26:
        return 0.0, 0.0, 0.0
    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)
    macd = ema12 - ema26
    signal = macd
    histogram = macd - signal
    return round(macd, 2), round(signal, 2), round(histogram, 2)

def calculate_bollinger_bands(closes: list[float], period: int = 20, std_dev: float = 2) -> tuple[float, float, float]:
    if len(closes) < period:
        return 0.0, 0.0, 0.0
    recent = closes[-period:]
    middle = sum(recent) / period
    variance = sum((x - middle) ** 2 for x in recent) / period
    std = variance ** 0.5
    return round(middle + std_dev * std, 2), round(middle, 2), round(middle - std_dev * std, 2)

def detect_rsi_divergence(rsi: float, closes: list[float]) -> str:
    if len(closes) < 10:
        return 'none'
    recent_closes = closes[-10:]
    price_trend = recent_closes[-1] - recent_closes[0]
    if price_trend < 0 and rsi > 50:
        return 'bullish'
    elif price_trend > 0 and rsi < 50:
        return 'bearish'
    return 'none'

def calculate_pivot_points(high: float, low: float, close: float) -> dict:
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    return {
        'pivot': round(pivot, 2),
        'r1': round(r1, 2),
        's1': round(s1, 2),
        'r2': round(r2, 2),
        's2': round(s2, 2)
    }

def get_signal_from_factors(rsi: float, ema20: float, ema50: float, volume_ratio: float, 
                           high_low_range: float, macd: float, macd_signal: float, 
                           macd_hist: float, bb_upper: float, bb_middle: float, bb_lower: float,
                           rsi_divergence: str, pivot: dict) -> tuple[str, str, float, float]:
    long_score = short_score = 0
    
    if rsi < 30: long_score += 2
    elif rsi > 70: short_score += 2
    elif rsi < 40: long_score += 1
    elif rsi > 60: short_score += 1
    
    if ema20 > ema50: long_score += 1
    else: short_score += 1
    
    if macd > macd_signal and macd_hist > 0: long_score += 1
    elif macd < macd_signal and macd_hist < 0: short_score += 1
    
    if bb_upper > 0 and bb_lower > 0:
        bb_position = (bb_middle - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
        if bb_position < 0.2: long_score += 1
        elif bb_position > 0.8: short_score += 1
    
    if volume_ratio > 1.5:
        if long_score > short_score: long_score += 1
        else: short_score += 1
    
    if rsi_divergence == 'bullish': long_score += 1
    elif rsi_divergence == 'bearish': short_score += 1
    
    if pivot:
        if bb_middle > pivot['pivot']: long_score += 0.5
        else: short_score += 0.5
    
    if long_score >= 4:
        return "LONG", "🚀 Strong Bullish Setup", long_score, short_score
    elif short_score >= 4:
        return "SHORT", "🔥 Strong Bearish Setup", long_score, short_score
    elif long_score > short_score:
        return "LONG", "⚡ Mild Bullish Bias", long_score, short_score
    elif short_score > long_score:
        return "SHORT", "⚠️ Mild Bearish Bias", long_score, short_score
    return "HOLD", "➡️ Neutral - Wait for Setup", long_score, short_score

def format_price(price: float) -> str:
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.2f}"
    elif price >= 0.01:
        return f"${price:.4f}"
    return f"${price:.6f}"

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "crypto-snapshot-pro",
        "proxy_enabled": USE_PROXY
    }
