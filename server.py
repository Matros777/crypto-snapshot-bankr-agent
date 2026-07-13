"""
Crypto Snapshot Pro — x402 Agent (Bankr) - ТОЛЬКО СИГНАЛЫ
"""

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
import time
import base64
import json
import logging
import sys
import os
from typing import Optional, Any
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

AGENTICMARKET_SECRET = os.getenv("AGENTICMARKET_SECRET", "")

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

MIN_AMOUNT = 25000

# ============================================================
# ПРОВЕРКА ТОКЕНА (ОТКЛЮЧЕНА)
# ============================================================

def verify_agentic_token(request: Request) -> bool:
    return True

# ============================================================
# СОЗДАЕМ ГЛАВНОЕ ПРИЛОЖЕНИЕ
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
                        content = data.get("message", {}).get("content", str(data))
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
                                "message": "Payment required or API error"
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
async def mcp_health(request: Request):
    return {"status": "ok", "service": "MCP Server", "version": "1.0.0"}

app.mount("/mcp", mcp_app)
logger.info("✅ MCP server mounted at /mcp")

# ============================================================
# ГЛАВНАЯ СТРАНИЦА — МИНИМАЛЬНЫЙ ОТВЕТ (BANKR САМ ДОБАВИТ ПАРАМЕТРЫ)
# ============================================================

@app.get("/")
async def root(request: Request):
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        return RedirectResponse(url="/app")
    
    # ✅ Bankr сам подставит свои платежные параметры
    return Response(
        status_code=402,
        content=json.dumps({"status": "Payment Required"}),
        media_type="application/json"
    )

# ============================================================
# ❌ ЯНДЕКС ВЕРИФИКАЦИЯ - УДАЛЕНА
# ============================================================
# @app.get("/yandex_d100e212bdd18c7b.html")
# async def yandex_verify():
#     return HTMLResponse("""
#     <html>
#         <head>
#             <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
#         </head>
#         <body>Verification: d100e212bdd18c7b</body>
#     </html>
#     """)

# ============================================================
# ПЕРЕМЕННЫЕ И ФУНКЦИИ
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
    price = signal_data.get('price', 0)
    change = signal_data.get('change', 0)
    volume_ratio = signal_data.get('volume_ratio', 1.0)
    conviction = signal_data.get('conviction', 'MEDIUM')
    entry = signal_data.get('entry', 0)
    target = signal_data.get('target', 0)
    stop = signal_data.get('stop', 0)
    risk_reward = signal_data.get('risk_reward', 0)
    support = signal_data.get('support', 0)
    resistance = signal_data.get('resistance', 0)
    ema20 = signal_data.get('ema20', 0)
    ema50 = signal_data.get('ema50', 0)

    lines = []

    if signal == "LONG":
        lines.append("📊 MARKET ASSESSMENT:")
        lines.append(f"Bullish momentum detected with price above EMA(20) and EMA(50). RSI at {rsi:.1f} suggests {'strong' if rsi < 70 else 'moderate'} buying pressure. Volume {'confirms' if volume_ratio > 1.5 else 'does not fully confirm'} the move.")
    elif signal == "SHORT":
        lines.append("📊 MARKET ASSESSMENT:")
        lines.append(f"Bearish signals present with {'overbought RSI' if rsi > 70 else 'weakening momentum'}. Price showing signs of exhaustion. Volume {'supports' if volume_ratio > 1.5 else 'does not strongly support'} downside.")
    else:
        lines.append("📊 MARKET ASSESSMENT:")
        lines.append(f"Mixed signals with RSI at {rsi:.1f} (neutral). Price trading between support and resistance. Wait for clear breakout or breakdown.")

    rec = "LONG" if signal == "LONG" else "SHORT" if signal == "SHORT" else "HOLD"
    reason = f"Technical indicators {'strongly' if conviction in ['VERY HIGH', 'HIGH'] else 'moderately'} support this position."
    lines.append(f"\n🎯 RECOMMENDATION: {rec}")
    lines.append(reason)

    if signal == "LONG":
        pred = f"+{2 + (rsi / 100) * 3:.1f}%"
        direction = "UP"
    elif signal == "SHORT":
        pred = f"-{2 + ((100 - rsi) / 100) * 3:.1f}%"
        direction = "DOWN"
    else:
        pred = f"±{(rsi / 100) * 2:.1f}%"
        direction = "SIDEWAYS"
    lines.append(f"\n📈 24H PRICE PREDICTION:")
    lines.append(f"Price expected to move {direction} by approximately {pred}")

    lines.append(f"\n📍 ENTRY ZONE: ${entry:.2f}")
    if signal == "LONG":
        t1 = entry * 1.03
        t2 = entry * 1.05
        sl = entry * 0.97
        lines.append(f"🎯 TARGET 1: ${t1:.2f} (+3%)")
        lines.append(f"🎯 TARGET 2: ${t2:.2f} (+5%)")
        lines.append(f"🛑 STOP LOSS: ${sl:.2f} (-3%)")
    elif signal == "SHORT":
        t1 = entry * 0.97
        t2 = entry * 0.95
        sl = entry * 1.03
        lines.append(f"🎯 TARGET 1: ${t1:.2f} (-3%)")
        lines.append(f"🎯 TARGET 2: ${t2:.2f} (-5%)")
        lines.append(f"🛑 STOP LOSS: ${sl:.2f} (+3%)")
    else:
        lines.append(f"🎯 TARGET: ${target:.2f}")
        lines.append(f"🛑 STOP: ${stop:.2f}")

    risk = "Low" if conviction in ["VERY HIGH", "HIGH"] else "Medium" if conviction == "MEDIUM" else "High"
    risk_note = "Strong technical confirmation" if conviction in ["VERY HIGH", "HIGH"] else "Mixed signals present" if conviction == "MEDIUM" else "Weak confirmation"
    lines.append(f"\n⚠️ RISK: {risk}")
    lines.append(f"{risk_note} - Position sizing recommended.")

    conf = 85 if conviction == "VERY HIGH" else 70 if conviction == "HIGH" else 55 if conviction == "MEDIUM" else 40
    lines.append(f"\n🎯 CONFIDENCE: {conf}%")

    lines.append(f"\n📌 KEY LEVELS:")
    lines.append(f"  Support: ${support:.2f}")
    lines.append(f"  Resistance: ${resistance:.2f}")

    if signal == "LONG":
        final = f"Consider LONG position with entry at ${entry:.2f}, target ${t1:.2f}, stop ${sl:.2f}. Monitor resistance at ${resistance:.2f} for potential exit."
    elif signal == "SHORT":
        final = f"Consider SHORT position with entry at ${entry:.2f}, target ${t1:.2f}, stop ${sl:.2f}. Monitor support at ${support:.2f} for potential exit."
    else:
        final = f"Recommend HOLD. Wait for clear breakout above ${resistance:.2f} or breakdown below ${support:.2f} before entering."

    lines.append(f"\n💡 FINAL RECOMMENDATION:")
    lines.append(final)

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

    for model in ASI_MODELS:
        try:
            if not ASI_API_KEY:
                logger.warning("No ASI API key, using fallback")
                return generate_fallback_analysis(signal_data)

            logger.info(f"Trying ASI model: {model['name']}")

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
                    ai_analysis = data["choices"][0]["message"]["content"]
                    logger.info(f"AI analysis generated via {model['name']}")
                    return ai_analysis
                else:
                    logger.warning(f"ASI {model['name']} error: {response.status_code}")
                    continue

        except Exception as e:
            logger.error(f"ASI {model.get('name', 'unknown')} error: {e}")
            continue

    logger.info("All ASI models failed, using fallback analysis")
    return generate_fallback_analysis(signal_data)

ALCHEMY_URL = os.getenv("ALCHEMY_URL", "https://base-mainnet.g.alchemy.com/v2/U8khpdvO0rAwu9ojyBOpr")
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
PAYTO_ADDRESS = "0x5b7efd37546d6BB02463339cEaDdD80997aC97B3"
paid_tx_cache = {}

async def verify_tx_payment(tx_hash: str) -> bool:
    if tx_hash in paid_tx_cache:
        return paid_tx_cache[tx_hash]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                ALCHEMY_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_getTransactionReceipt",
                    "params": [tx_hash],
                    "id": 1
                }
            )

            if response.status_code != 200:
                paid_tx_cache[tx_hash] = False
                return False

            data = response.json()
            receipt = data.get("result")

            if not receipt or receipt.get("status") != "0x1":
                paid_tx_cache[tx_hash] = False
                return False

            logs = receipt.get("logs", [])
            for log in logs:
                if log.get("address", "").lower() == USDC_ADDRESS.lower():
                    topics = log.get("topics", [])
                    if len(topics) >= 3:
                        to_address = "0x" + topics[2][-40:]
                        if to_address.lower() == PAYTO_ADDRESS.lower():
                            paid_tx_cache[tx_hash] = True
                            logger.info(f"Payment verified for tx: {tx_hash}")
                            return True

            paid_tx_cache[tx_hash] = False
            return False

    except Exception as e:
        logger.error(f"TX verification error: {e}")
        paid_tx_cache[tx_hash] = False
        return False

class AgentResponse(BaseModel):
    message: dict

# ============================================================
# ❌ ВЕСЬ X402 УДАЛЕН - BANKR САМ ОБРАБАТЫВАЕТ ПЛАТЕЖИ!
# ============================================================

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
            logger.info(f"Using proxy: {PROXY_HOST}:{PROXY_PORT}")
            async with httpx.AsyncClient(
                timeout=15.0,
                proxy=PROXY_URL
            ) as client:
                response = await client.get(
                    f"{BINANCE_API}/{endpoint}",
                    params=params
                )
        else:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{BINANCE_API}/{endpoint}",
                    params=params
                )

        if response.status_code != 200:
            logger.error(f"Binance error: {response.status_code}")
            raise HTTPException(status_code=503, detail="Market data unavailable")

        data = response.json()
        _cache[cache_key] = {"data": data, "time": now}
        return data

    except httpx.ProxyError as e:
        logger.error(f"Proxy error: {e}")
        logger.info("Retrying without proxy...")
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{BINANCE_API}/{endpoint}",
                params=params
            )
            if response.status_code == 200:
                data = response.json()
                _cache[cache_key] = {"data": data, "time": now}
                return data
            raise HTTPException(status_code=503, detail="Market data unavailable")

    except Exception as e:
        logger.error(f"Request error: {e}")
        raise HTTPException(status_code=503, detail="Market data unavailable")

async def fetch_ticker(symbol: str) -> dict:
    cache_key = f"ticker_{symbol}"
    now = time.time()
    if cache_key in _cache and now - _cache[cache_key]["time"] < _CACHE_TTL:
        return _cache[cache_key]["data"]

    try:
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
        logger.info(f"{symbol} price: ${price}, change: {result['change']:.2f}%")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Binance error: {e}")
        raise HTTPException(status_code=503, detail="Market data unavailable")

async def fetch_klines(symbol: str, interval: str = "1d", limit: int = 50) -> list[dict]:
    cache_key = f"klines_{symbol}_{interval}_{limit}"
    now = time.time()
    if cache_key in _cache and now - _cache[cache_key]["time"] < _CACHE_TTL:
        return _cache[cache_key]["data"]

    try:
        data = await fetch_binance("klines", {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        })

        if not data or len(data) < 5:
            raise HTTPException(status_code=503, detail="Insufficient historical data")

        klines = []
        for candle in data:
            klines.append({
                'close': float(candle[4]),
                'high': float(candle[2]),
                'low': float(candle[3]),
                'volume': float(candle[5]),
                'time': int(candle[0])
            })

        _cache[cache_key] = {"data": klines, "time": now}
        return klines

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Binance klines error: {e}")
        raise HTTPException(status_code=503, detail="Historical data unavailable")

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
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)

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
    macd_values = [macd]
    signal = calculate_ema(macd_values, 9) if len(macd_values) >= 9 else macd
    histogram = macd - signal
    return round(macd, 2), round(signal, 2), round(histogram, 2)

def calculate_bollinger_bands(closes: list[float], period: int = 20, std_dev: float = 2) -> tuple[float, float, float]:
    if len(closes) < period:
        return 0.0, 0.0, 0.0
    recent = closes[-period:]
    middle = sum(recent) / period
    variance = sum((x - middle) ** 2 for x in recent) / period
    std = variance ** 0.5
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return round(upper, 2), round(middle, 2), round(lower, 2)

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

def get_signal_from_factors(rsi: float, price_ema20: float, price_ema50: float,
                           volume_ratio: float, high_low_range: float,
                           macd: float, macd_signal: float, macd_hist: float,
                           bb_upper: float, bb_middle: float, bb_lower: float,
                           rsi_divergence: str, pivot: dict) -> tuple[str, str, int, int]:
    long_score = short_score = 0

    if rsi < 30: long_score += 2
    elif rsi > 70: short_score += 2
    elif rsi < 40: long_score += 1
    elif rsi > 60: short_score += 1

    if price_ema20 > price_ema50:
        long_score += 1
    else:
        short_score += 1

    if macd > macd_signal and macd_hist > 0:
        long_score += 1
    elif macd < macd_signal and macd_hist < 0:
        short_score += 1

    if bb_upper > 0 and bb_lower > 0:
        bb_position = (bb_middle - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
        if bb_position < 0.2:
            long_score += 1
        elif bb_position > 0.8:
            short_score += 1

    if volume_ratio > 1.5:
        if long_score > short_score:
            long_score += 1
        else:
            short_score += 1

    if rsi_divergence == 'bullish':
        long_score += 1
    elif rsi_divergence == 'bearish':
        short_score += 1

    if high_low_range > 0.03:
        if long_score > short_score:
            long_score += 1
        else:
            short_score += 1

    if pivot:
        current_price = bb_middle
        if current_price > pivot['pivot']:
            long_score += 0.5
        else:
            short_score += 0.5

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
# ГЛАВНЫЙ API — POST ОБРАБОТЧИК (ТОЛЬКО СИГНАЛЫ, БЕЗ X402)
# ============================================================

@app.post("/")
async def crypto_snapshot(request: Request):
    """
    POST — генерирует сигнал.
    Bankr сам обрабатывает оплату и вызывает этот эндпоинт ТОЛЬКО ПОСЛЕ ОПЛАТЫ.
    НИКАКОЙ X402 ЛОГИКИ ЗДЕСЬ НЕ НУЖНО!
    """

    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    symbol = body.get("symbol", "").strip()

    # ============================================================
    # ✅ ВЕБ-ИНТЕРФЕЙС — ОСТАВЛЯЕМ КАК ЕСТЬ!
    # ============================================================
    tx_hash = body.get("tx_hash")
    if tx_hash:
        logger.info(f"🔍 Verifying tx: {tx_hash}")
        if not await verify_tx_payment(tx_hash):
            return Response(
                content="Payment verification failed. Transaction not found or invalid.",
                status_code=402
            )
        logger.info(f"✅ Tx {tx_hash} verified")
        result = await generate_signal(symbol or "BTC")
        return AgentResponse(message={"role": "assistant", "content": result})

    # ============================================================
    # ❌ X402 (ДЛЯ АГЕНТОВ) — ПОЛНОСТЬЮ УДАЛЕН!
    #    Bankr сам обрабатывает оплату.
    #    Этот эндпоинт вызывается ТОЛЬКО ПОСЛЕ ОПЛАТЫ.
    # ============================================================

    # ============================================================
    # ЕСЛИ НЕТ symbol — ПОДСКАЗКА
    # ============================================================
    if not symbol:
        return AgentResponse(message={
            "role": "assistant",
            "content": "📊 CRYPTO SNAPSHOT PRO\n\nSend a symbol to analyze.\n\nExamples:\n• BTC\n• ETH\n• SOL\n• DOGE\n• XRP\n\nUsage: POST {\"symbol\": \"BTC\"}"
        })

    # ============================================================
    # ГЕНЕРИРУЕМ СИГНАЛ
    # ============================================================
    result = await generate_signal(symbol)
    return AgentResponse(message={"role": "assistant", "content": result})

# ============================================================
# ГЕНЕРАЦИЯ СИГНАЛА
# ============================================================

async def generate_signal(symbol: str) -> str:
    """Генерирует торговый сигнал для указанного символа."""
    try:
        symbol = symbol.upper()
        symbol = symbol.replace("USDT", "").replace("USD", "").replace("NODE", "")
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

        if rsi < 30:
            rsi_status = "oversold"
        elif rsi > 70:
            rsi_status = "overbought"
        else:
            rsi_status = "neutral"

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

        result = f"""
╔══════════════════════════════════════════════════════════════════╗
║  📊 CRYPTO SNAPSHOT PRO — {symbol.replace('USDT', '/USDT')}          ║
╚══════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════╗
║  🎯 TECHNICAL SIGNAL                                           ║
╠══════════════════════════════════════════════════════════════════╣
║  {signal_desc} ║
║  Conviction: {conviction:<10}  |  Score: {long_score:.1f}🟢LONG / {short_score:.1f}🔴SHORT    ║
║  Reason: {'Bullish factors dominate.' if long_score > short_score else 'Bearish factors dominate.' if short_score > long_score else 'Mixed signals. Wait for confirmation.'} ║
╚══════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════╗
║  📈 TECHNICAL INDICATORS                                       ║
╠══════════════════════════════════════════════════════════════════╣
║  Price:  {format_price(current_price):<20}  24h Change: {change_24h:+.2f}% ║
║  RSI(14): {rsi:.1f} ({rsi_status}){' ' * (40 - len(f'{rsi:.1f} ({rsi_status})'))}║
║  EMA(20): {format_price(ema20):<20}  EMA(50): {format_price(ema50)} ║
║  Volume Ratio: {volume_ratio:.2f}x{' ' * (30 - len(f'{volume_ratio:.2f}x'))}║
╚══════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════╗
║  🎯 STRATEGY LEVELS                                            ║
╠══════════════════════════════════════════════════════════════════╣
║  Entry:  {format_price(entry):<20}  Target: {format_price(target)} ║
║  Stop:   {format_price(stop):<20}  Risk/Reward: 1:{risk_reward:.2f} ║
╚══════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════╗
║  🤖 PROFESSIONAL AI ANALYSIS                                   ║
╠══════════════════════════════════════════════════════════════════╣
{ai_analysis}
╚══════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════╗
║  📌 KEY LEVELS                                                ║
╠══════════════════════════════════════════════════════════════════╣
║  Support:  {format_price(support):<20}  Resistance: {format_price(resistance)} ║
║  24h High: {format_price(high_24h):<20}  24h Low:  {format_price(low_24h)} ║
╚══════════════════════════════════════════════════════════════════╝

📚 Resources:
📖 Full Guide: https://gist.github.com/Matros777/c5d95532248eaaf2b86fd04f8a2753b7
🐦 Twitter: https://x.com/VitalijMatros
🌐 OpenX402: https://openx402.ai/projects/0x5b7efd37546d6bb02463339ceaddd80997ac97b3

⚠️  Risk Disclosure: This is NOT financial advice. Always manage risk. Past performance does not guarantee future results.
"""

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

# ============================================================
# ❌ STATIC И /app - ЗАКОММЕНТИРОВАНЫ!
# ============================================================
# app.mount("/static", StaticFiles(directory="static"), name="static")
# 
# @app.get("/app")
# async def web_app():
#     try:
#         with open("static/index.html", "r", encoding="utf-8") as f:
#             return HTMLResponse(f.read())
#     except FileNotFoundError:
#         return HTMLResponse("<h1>Web interface not found</h1>", status_code=404)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "crypto-snapshot-pro", "proxy_enabled": USE_PROXY}

# ============================================================
# ЭНДПОИНТ ДЛЯ БАЛАНСА
# ============================================================

class BalanceRequest(BaseModel):
    address: str

@app.post("/api/balance")
async def get_balance(request: BalanceRequest):
    try:
        address = request.address

        if not address or not address.startswith("0x") or len(address) != 42:
            return {"error": "Invalid address", "balance": "0"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            data = {
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{
                    "to": USDC_ADDRESS,
                    "data": f"0x70a08231000000000000000000000000{address[2:].lower()}"
                }, "latest"],
                "id": 1
            }

            response = await client.post(ALCHEMY_URL, json=data)

            if response.status_code == 200:
                result = response.json()
                if "result" in result and result["result"] != "0x":
                    balance_wei = int(result["result"], 16)
                    balance = balance_wei / 10**6
                    return {"balance": str(balance), "usdc": balance}

            return {"balance": "0"}

    except Exception as e:
        logger.error(f"Balance error: {e}")
        return {"balance": "0", "error": str(e)}

@app.get("/api/balance/{address}")
async def get_balance_get(address: str):
    return await get_balance(BalanceRequest(address=address))
