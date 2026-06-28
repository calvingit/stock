"""
ETF均线策略回测工具 - FastAPI后端
数据来源: 万得Wind金融数据
"""
import json
import subprocess
import os
from collections import Counter
from datetime import datetime
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

app = FastAPI(title="ETF均线策略回测工具")

WIND_CLI_DIR = os.path.expanduser(os.getenv("WIND_CLI_DIR", os.path.join(os.path.dirname(__file__), "")))
CACHE_DIR = os.path.expanduser(os.getenv("ETF_CACHE_DIR", "/tmp/etf_backtest_cache"))
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_kline(etf_code: str, begin: str, end: str) -> dict:
    """从Wind获取日K线数据,返回 {closes:[], volumes:[], dates:[]}"""
    cache_key = f"{etf_code}_{begin}_{end}"
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    # 缓存24小时
    if os.path.exists(cache_file):
        age = datetime.now().timestamp() - os.path.getmtime(cache_file)
        if age < 86400:
            with open(cache_file) as f:
                data = json.load(f)
                if data and isinstance(data, dict):
                    return data
    
    cmd = [
        "node", "scripts/cli.mjs", "call", "fund_data", "get_fund_kline",
        json.dumps({
            "windcode": etf_code,
            "begin_date": begin.replace("-", ""),
            "end_date": end.replace("-", ""),
            "period": "10"
        })
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, 
                               timeout=60, cwd=WIND_CLI_DIR)
        if result.returncode != 0:
            return {}
        
        outer = json.loads(result.stdout)
        inner = json.loads(outer["content"][0]["text"])
        if inner.get("error"):
            return {}
        
        rows = inner["data"]["rows"]
        closes = [float(r[2]) for r in rows]
        volumes = [float(r[6]) for r in rows]
        dates = [r[-1] for r in rows]
        
        data = {"closes": closes, "volumes": volumes, "dates": dates}
        with open(cache_file, 'w') as f:
            json.dump(data, f)
        
        return data
    except Exception as e:
        print(f"Wind fetch error for {etf_code}: {e}")
        return {}


# ============ 右侧买入时机 — 信号计算函数 ============

def calc_ema(data: list, period: int) -> list:
    """计算 EMA，返回与 data 等长的列表（前 period-1 个为 None）"""
    if len(data) < period:
        return [None] * len(data)
    k = 2 / (period + 1)
    ema = [None] * (period - 1) + [sum(data[:period]) / period]
    for i in range(period, len(data)):
        ema.append(data[i] * k + ema[-1] * (1 - k))
    return ema


def calc_macd(closes: list, fast=12, slow=26, signal=9) -> dict:
    """返回 {dif:[], dea:[], histogram:[]}"""
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    n = len(closes)
    dif = [None] * n
    for i in range(n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            dif[i] = ema_fast[i] - ema_slow[i]
    dea = calc_ema([d if d is not None else 0 for d in dif], signal)
    start = slow + signal - 2
    for i in range(start):
        if i < len(dea):
            dea[i] = None
    histogram = [None] * n
    for i in range(n):
        if dif[i] is not None and dea[i] is not None:
            histogram[i] = (dif[i] - dea[i]) * 2
    return {"dif": dif, "dea": dea, "histogram": histogram}


def calc_rsi(closes: list, period=14) -> list:
    """Wilder RSI，返回等长列表"""
    if len(closes) < period + 1:
        return [None] * len(closes)
    rsi = [None] * period
    gains = losses = 0.0
    for i in range(1, period + 1):
        chg = closes[i] - closes[i - 1]
        if chg > 0:
            gains += chg
        else:
            losses += abs(chg)
    avg_gain = gains / period
    avg_loss = losses / period
    rs = avg_gain / avg_loss if avg_loss != 0 else 100.0
    rsi.append(100.0 - 100.0 / (1.0 + rs))
    for i in range(period + 1, len(closes)):
        chg = closes[i] - closes[i - 1]
        gain = chg if chg > 0 else 0.0
        loss = abs(chg) if chg < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else 100.0
        rsi.append(100.0 - 100.0 / (1.0 + rs))
    return rsi


def calc_sma(data: list, period: int) -> list:
    """简单移动平均"""
    if len(data) < period:
        return [None] * len(data)
    sma = [None] * (period - 1)
    window = sum(data[:period])
    sma.append(window / period)
    for i in range(period, len(data)):
        window += data[i] - data[i - period]
        sma.append(window / period)
    return sma


def find_recent_low(closes: list, window=120) -> float:
    """找近 window 日内最低价"""
    if len(closes) < window:
        return min(closes) if closes else 0.0
    return min(closes[-window:])


def find_52w_low(closes: list) -> float:
    """找52周(约250日)最低价"""
    return find_recent_low(closes, min(250, len(closes)))


# ============ 波段策略(周线) ============

def fetch_weekly(etf_code: str, begin: str, end: str) -> dict:
    """获取周线数据"""
    cache_key = f"w_{etf_code}_{begin}_{end}"
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    if os.path.exists(cache_file):
        age = datetime.now().timestamp() - os.path.getmtime(cache_file)
        if age < 86400:
            with open(cache_file) as f:
                data = json.load(f)
                if data and isinstance(data, dict):
                    return data
    
    cmd = [
        "node", "scripts/cli.mjs", "call", "fund_data", "get_fund_kline",
        json.dumps({
            "windcode": etf_code,
            "begin_date": begin.replace("-", ""),
            "end_date": end.replace("-", ""),
            "period": "11"
        })
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=WIND_CLI_DIR)
        if result.returncode != 0:
            return {}
        outer = json.loads(result.stdout)
        inner = json.loads(outer["content"][0]["text"])
        if inner.get("error"):
            return {}
        rows = inner["data"]["rows"]
        data = {
            "dates": [r[-1] for r in rows],
            "opens": [float(r[1]) for r in rows],
            "closes": [float(r[2]) for r in rows],
            "highs": [float(r[3]) for r in rows],
            "lows": [float(r[4]) for r in rows],
            "volumes": [float(r[6]) for r in rows],
        }
        with open(cache_file, 'w') as f:
            json.dump(data, f)
        return data
    except Exception as e:
        print(f"Weekly fetch error for {etf_code}: {e}")
        return {}


def calc_kdj(highs, lows, closes, n=9):
    K, D, J = [], [], []
    prev_k, prev_d = 50.0, 50.0
    for i in range(len(closes)):
        if i < n - 1:
            K.append(None); D.append(None); J.append(None)
            continue
        h = max(highs[i-n+1:i+1])
        l = min(lows[i-n+1:i+1])
        rsv = (closes[i] - l) / (h - l) * 100 if h != l else 50
        k_val = 2/3 * prev_k + 1/3 * rsv
        d_val = 2/3 * prev_d + 1/3 * k_val
        j_val = 3 * k_val - 2 * d_val
        K.append(round(k_val, 2)); D.append(round(d_val, 2)); J.append(round(j_val, 2))
        prev_k, prev_d = k_val, d_val
    return K, D, J


def calc_rsi(closes, n=14):
    rsi = [None] * n
    gains = [max(closes[i]-closes[i-1], 0) for i in range(1, n+1)]
    losses = [max(closes[i-1]-closes[i], 0) for i in range(1, n+1)]
    avg_gain = sum(gains)/n
    avg_loss = sum(losses)/n
    rsi.append(round(100 - 100/(1+avg_gain/avg_loss), 2) if avg_loss > 0 else 100.0)
    for i in range(n+1, len(closes)):
        diff = closes[i] - closes[i-1]
        gain = max(diff, 0); loss = max(-diff, 0)
        avg_gain = (avg_gain*(n-1)+gain)/n
        avg_loss = (avg_loss*(n-1)+loss)/n
        rsi.append(round(100 - 100/(1+avg_gain/avg_loss), 2) if avg_loss > 0 else 100.0)
    return rsi


def calc_rps20(closes):
    ret_20w = [None]*20
    for i in range(20, len(closes)):
        ret_20w.append((closes[i]-closes[i-20])/closes[i-20]*100)
    rps = [None]*len(closes)
    all_rets = [r for r in ret_20w if r is not None]
    for i in range(len(closes)):
        if ret_20w[i] is None:
            continue
        rank = sum(1 for r in all_rets if r < ret_20w[i]) / len(all_rets) * 100
        rps[i] = round(rank, 2)
    return rps


def run_band_backtest(data: dict, params: dict):
    """
    波段策略回测
    params:
        buy_k, buy_rsi, buy_rps: 买入阈值 (KDJ_K < X, RSI < X, RPS20 >= X)
        sell_k, sell_rsi, sell_rps: 卖出阈值 (KDJ_K > X, RSI > X, RPS20 < X)
    """
    closes = data["closes"]
    highs = data["highs"]
    lows = data["lows"]
    
    K, D, J = calc_kdj(highs, lows, closes)
    rsi_vals = calc_rsi(closes)
    rps_vals = calc_rps20(closes)
    
    bk = int(params.get("buy_k", 30))
    br = int(params.get("buy_rsi", 40))
    bp = int(params.get("buy_rps", 10))
    sk = int(params.get("sell_k", 80))
    sr = int(params.get("sell_rsi", 70))
    sp = int(params.get("sell_rps", 20))
    initial = float(params.get("initial_capital", 1000000))
    commission = 0.0003
    
    warmup = 20
    cap = initial
    shares = 0
    in_pos = False
    cost_basis = 0
    trades = []
    
    nav_series = [initial] * warmup
    
    for i in range(warmup, len(closes)):
        p = closes[i]
        kv, rv, pv = K[i], rsi_vals[i], rps_vals[i]
        
        if None in (kv, rv, pv):
            nav_series.append(cap + shares * p)
            continue
        
        # 卖出判断
        if in_pos:
            sell_reason = None
            if kv > sk:
                sell_reason = f"KDJ_K={kv:.0f}>{sk}"
            elif rv > sr:
                sell_reason = f"RSI={rv:.0f}>{sr}"
            elif pv < sp:
                sell_reason = f"RPS20={pv:.0f}<{sp}"
            
            if sell_reason:
                proceeds = shares * p * (1 - commission)
                cap += proceeds
                profit_pct = (proceeds - shares*cost_basis*(1+commission)) / (shares*cost_basis) * 100
                trades.append({
                    "type": "sell", "idx": i, "price": round(p, 4),
                    "reason": sell_reason, "profit_pct": round(profit_pct, 2)
                })
                shares = 0
                in_pos = False
        
        # 买入判断
        if not in_pos:
            if kv < bk and rv < br and pv >= bp:
                shares = int(cap / (p * (1 + commission)))
                cost = shares * p * (1 + commission)
                cap -= cost
                cost_basis = p
                in_pos = True
                trades.append({
                    "type": "buy", "idx": i, "price": round(p, 4),
                    "reason": f"K={kv:.0f}<{bk} RSI={rv:.0f}<{br} RPS={pv:.0f}≥{bp}"
                })
        
        nav_series.append(round(cap + shares * p, 2))
    
    # 期末平仓
    if in_pos:
        p = closes[-1]
        cap += shares * p * (1 - commission)
        trades.append({"type": "sell_final", "idx": len(closes)-1, "price": round(p, 4), "reason": "期末平仓"})
        nav_series[-1] = round(cap, 2)
    
    final_value = cap
    total_return = (final_value - initial) / initial * 100
    
    buys = [t for t in trades if t["type"] == "buy"]
    sells = [t for t in trades if "sell" in t["type"]]
    
    gains = []
    for b, s in zip(buys, sells):
        g = s.get("profit_pct", 0)
        if g == 0:
            proceeds = s["price"] * 100 * (1 - commission)
            cost = b["price"] * 100 * (1 + commission)
            g = (proceeds - cost) / cost * 100
        gains.append(round(g, 2))
    
    # 最大回撤
    peak = initial
    max_dd = 0
    for nav in nav_series:
        if nav > peak:
            peak = nav
        dd = (peak - nav) / peak * 100
        max_dd = max(max_dd, dd)
    
    bh_return = (closes[-1] - closes[warmup]) / closes[warmup] * 100
    
    marks = [{"idx": t["idx"], "type": t["type"], "price": t["price"]} for t in trades]
    
    return {
        "final_value": round(final_value, 2),
        "total_return": round(total_return, 2),
        "buy_hold_return": round(bh_return, 2),
        "alpha": round(total_return - bh_return, 2),
        "trade_count": len(buys),
        "win_rate": round(sum(1 for g in gains if g > 0) / len(gains) * 100, 1) if gains else 0,
        "avg_gain": round(sum(gains)/len(gains), 2) if gains else 0,
        "worst_trade": round(min(gains), 2) if gains else 0,
        "max_drawdown": round(max_dd, 2),
        "skipped_volume": 0,
        "skipped_pause": 0,
        "sharpe_approx": round(sum(gains)/len(gains)/(__import__('statistics').stdev(gains) if len(gains)>1 else 1), 2) if gains and len(gains)>1 else 0,
        "gains": gains,
        "marks": marks,
        "trades": trades,
        "nav_series": nav_series,
        "closes": closes[warmup:],
        "min_days": warmup,
    }



def ma(arr, idx, n):
    if idx < n - 1:
        return None
    return sum(arr[idx-n+1:idx+1]) / n


def run_backtest(data: dict, params: dict):
    """
    运行均线多头回测
    data: {"closes": [...], "volumes": [...], "dates": [...]}
    params:
        fast_ma, mid_ma, slow_ma: 均线周期
        hard_stop: 硬止损比例 (0=不启用)
        trail_stop: 移动止损比例 (0=不启用)
        initial_capital: 初始资金
        volume_confirm: 成交量确认倍数 (0=不启用, 1.2=放量1.2倍才买入)
        pause_after_losses: 连亏N笔后暂停天数 (0=不启用)
    """
    closes = data.get("closes", [])
    volumes = data.get("volumes", [])
    
    fast = int(params.get("fast_ma", 5))
    mid = int(params.get("mid_ma", 10))
    slow = int(params.get("slow_ma", 20))
    hard_stop = float(params.get("hard_stop", 0))
    trail_stop = float(params.get("trail_stop", 0))
    initial = float(params.get("initial_capital", 1000000))
    vol_mult = float(params.get("volume_confirm", 0))
    pause_losses = int(params.get("pause_after_losses", 0))
    pause_days = int(params.get("pause_days", 10))
    commission = 0.0003
    
    min_days = max(fast, mid, slow, 20)
    
    cap = initial
    shares = 0
    in_pos = False
    trades = []
    cost_basis = 0
    highest = 0
    entry_idx = 0
    
    # 连亏跟踪
    consecutive_losses = 0
    pause_until = -1  # 暂停到第几天
    skipped_by_volume = 0  # 统计
    skipped_by_pause = 0
    
    # 净值曲线
    nav_series = []
    for _ in range(min_days):
        nav_series.append(initial)
    
    for i in range(min_days - 1, len(closes)):
        p = closes[i]
        m_fast = ma(closes, i, fast)
        m_mid = ma(closes, i, mid)
        m_slow = ma(closes, i, slow)
        
        # 卖出判断
        if in_pos:
            if p > highest:
                highest = p
            
            sell_reason = None
            
            if hard_stop > 0:
                if (p - cost_basis) / cost_basis <= -hard_stop:
                    sell_reason = f"硬止损-{int(hard_stop*100)}%"
            
            if not sell_reason and trail_stop > 0 and highest > cost_basis:
                dd = (highest - p) / highest
                if dd >= trail_stop:
                    sell_reason = f"移动止损-{int(trail_stop*100)}%"
            
            if not sell_reason:
                if m_fast < m_mid:
                    sell_reason = f"{fast}MA死叉{mid}MA"
                elif m_fast < m_slow:
                    sell_reason = f"{fast}MA跌破{slow}MA"
            
            if sell_reason:
                proceeds = shares * p * (1 - commission)
                cap += proceeds
                profit_pct = (proceeds - (shares * cost_basis * (1 + commission))) / (shares * cost_basis) * 100
                trades.append({
                    "type": "sell", "idx": i, "price": round(p, 4),
                    "shares": shares, "amount": round(proceeds, 2),
                    "reason": sell_reason,
                })
                # 连亏跟踪
                if profit_pct < 0:
                    consecutive_losses += 1
                    if pause_losses > 0 and consecutive_losses >= pause_losses:
                        pause_until = i + pause_days
                else:
                    consecutive_losses = 0
                
                shares = 0
                in_pos = False
        
        # 买入判断
        if not in_pos:
            ma_signal = (m_fast and m_mid and m_slow and m_fast > m_mid > m_slow)
            if ma_signal:
                skip_buy = False
                # 连亏暂停
                if pause_losses > 0 and i < pause_until:
                    skipped_by_pause += 1
                    skip_buy = True
                # 成交量确认
                if not skip_buy and vol_mult > 0 and i >= 20:
                    avg_vol = sum(volumes[i-19:i+1]) / 20
                    if volumes[i] < avg_vol * vol_mult:
                        skipped_by_volume += 1
                        skip_buy = True
                if not skip_buy:
                    shares = int(cap / (p * (1 + commission)))
                    cost = shares * p * (1 + commission)
                    cap -= cost
                    cost_basis = p
                    highest = p
                    entry_idx = i
                    in_pos = True
                    trades.append({
                        "type": "buy", "idx": i, "price": round(p, 4),
                        "shares": shares, "amount": round(cost, 2),
                        "reason": f"{fast}/{mid}/{slow}MA多头"
                    })
        
        nav = cap + (shares * p)
        nav_series.append(round(nav, 2))
    
    # 期末强制平仓
    if in_pos:
        p = closes[-1]
        proceeds = shares * p * (1 - commission)
        cap += proceeds
        trades.append({
            "type": "sell_final", "idx": len(closes)-1, "price": round(p, 4),
            "shares": shares, "amount": round(proceeds, 2),
            "reason": "期末平仓"
        })
        nav_series[-1] = round(cap, 2)
    
    final_value = cap
    total_return = (final_value - initial) / initial * 100
    
    # 统计
    buys = [t for t in trades if t["type"] == "buy"]
    sells = [t for t in trades if "sell" in t["type"]]
    
    gains = []
    for b, s in zip(buys, sells):
        g = (s["amount"] - b["amount"]) / b["amount"] * 100
        gains.append(round(g, 2))
    
    # 最大回撤
    peak = initial
    max_dd = 0
    for nav in nav_series:
        if nav > peak:
            peak = nav
        dd = (peak - nav) / peak * 100
        max_dd = max(max_dd, dd)
    
    # 买入持有
    bh_return = (closes[-1] - closes[min_days - 1]) / closes[min_days - 1] * 100
    
    # 夏普比率(简化)
    if len(gains) > 1:
        import statistics
        avg_g = sum(gains) / len(gains)
        std_g = statistics.stdev(gains) if len(gains) > 1 else 1
        sharpe = (avg_g / std_g) if std_g > 0 else 0
    else:
        sharpe = 0
    
    return {
        "final_value": round(final_value, 2),
        "total_return": round(total_return, 2),
        "buy_hold_return": round(bh_return, 2),
        "alpha": round(total_return - bh_return, 2),
        "trade_count": len(buys),
        "win_rate": round(sum(1 for g in gains if g > 0) / len(gains) * 100, 1) if gains else 0,
        "avg_gain": round(sum(gains)/len(gains), 2) if gains else 0,
        "worst_trade": round(min(gains), 2) if gains else 0,
        "max_drawdown": round(max_dd, 2),
        "sharpe_approx": round(sharpe, 2),
        "skipped_volume": skipped_by_volume,
        "skipped_pause": skipped_by_pause,
        "gains": gains,
        "trades": trades,
        "nav_series": nav_series,
        "closes": closes[min_days - 1:],
        "min_days": min_days,
    }


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(os.path.dirname(__file__), "templates", "index.html")) as f:
        return f.read()


@app.get("/api/backtest")
async def backtest_api(
    codes: str = Query(..., description="ETF代码,逗号分隔"),
    begin: str = Query("2023-06-01"),
    end: str = Query("2026-06-11"),
    fast_ma: int = Query(5),
    mid_ma: int = Query(10),
    slow_ma: int = Query(20),
    hard_stop: float = Query(0),
    trail_stop: float = Query(0),
    initial_capital: float = Query(1000000),
    volume_confirm: float = Query(0, description="成交量确认倍数(0=关闭,1.2=放量1.2倍)"),
    pause_after_losses: int = Query(0, description="连亏N笔后暂停(0=关闭,2=连亏2笔暂停10天)"),
    mode: str = Query("etf", description="模式: etf(多ETF单策略) / strategy(单ETF多策略)"),
    strategy_sets: str = Query("", description="多策略模式的JSON参数数组"),
):
    """
    ETF均线策略回测
    mode=etf: 多ETF对比同一策略
    mode=strategy: 单ETF对比多组策略参数
    """
    
    results = []
    base_params = {
        "fast_ma": fast_ma, "mid_ma": mid_ma, "slow_ma": slow_ma,
        "hard_stop": hard_stop, "trail_stop": trail_stop,
        "initial_capital": initial_capital,
        "volume_confirm": volume_confirm,
        "pause_after_losses": pause_after_losses,
    }
    
    if mode == "strategy":
        # 单ETF多策略模式
        etf_list = [c.strip() for c in codes.split(",") if c.strip()]
        if len(etf_list) != 1:
            raise HTTPException(400, "多策略模式下请提供单个ETF代码")
        code = etf_list[0]
        
        # 解析策略组
        if strategy_sets:
            try:
                sets = json.loads(strategy_sets)
            except json.JSONDecodeError:
                raise HTTPException(400, "策略参数JSON格式错误")
        else:
            sets = [base_params]
        
        kdata = fetch_kline(code, begin, end)
        if not kdata or not kdata.get("closes"):
            raise HTTPException(400, f"无法获取 {code} 数据")
        
        for idx, ps in enumerate(sets):
            p = {**base_params}
            p.update({k: v for k, v in ps.items() if v is not None})
            bt = run_backtest(kdata, p)
            
            label = f"{p['fast_ma']}/{p['mid_ma']}/{p['slow_ma']}"
            if p.get('trail_stop', 0) > 0:
                label += f" 移{int(p['trail_stop']*100)}%"
            if p.get('hard_stop', 0) > 0:
                label += f" 硬{int(p['hard_stop']*100)}%"
            if p.get('volume_confirm', 0) > 0:
                label += f" 量{p['volume_confirm']}x"
            if p.get('pause_after_losses', 0) > 0:
                label += f" 停{p['pause_after_losses']}"
            
            bt["code"] = code
            bt["label"] = label
            bt["strategy_params"] = p
            
            marks = []
            for t in bt.get("trades", []):
                marks.append({"idx": t["idx"], "type": t["type"], "price": t["price"]})
            bt["marks"] = marks
            bt["trade_summary"] = len(bt["trades"])
            bt.pop("trades", None)
            results.append(bt)
    else:
        # 多ETF单策略模式（原有逻辑）
        etf_list = [c.strip() for c in codes.split(",") if c.strip()]
        if not etf_list:
            raise HTTPException(400, "请提供至少一个ETF代码")
        if len(etf_list) > 5:
            raise HTTPException(400, "最多支持5个ETF同时对比")
        
        for code in etf_list:
            kdata = fetch_kline(code, begin, end)
            if not kdata or not kdata.get("closes"):
                results.append({"code": code, "error": f"无法获取{code}数据"})
                continue
            
            bt = run_backtest(kdata, base_params)
            bt["code"] = code
            
            marks = []
            for t in bt.get("trades", []):
                marks.append({"idx": t["idx"], "type": t["type"], "price": t["price"]})
            bt["marks"] = marks
            bt["trade_summary"] = len(bt["trades"])
            bt.pop("trades", None)
            results.append(bt)
    
    return JSONResponse({
        "mode": mode,
        "params": base_params,
        "period": f"{begin} ~ {end}",
        "results": results,
    })


@app.get("/api/backtest/band")
async def backtest_band(
    codes: str = Query(..., description="ETF代码,逗号分隔"),
    begin: str = Query("2021-01-01"),
    end: str = Query("2026-06-11"),
    buy_k: int = Query(30, description="买入: KDJ_K 低于此值"),
    buy_rsi: int = Query(40, description="买入: RSI 低于此值"),
    buy_rps: int = Query(10, description="买入: RPS20 不低于此值"),
    sell_k: int = Query(80, description="卖出: KDJ_K 高于此值"),
    sell_rsi: int = Query(70, description="卖出: RSI 高于此值"),
    sell_rps: int = Query(20, description="卖出: RPS20 低于此值"),
    initial_capital: float = Query(1000000),
):
    """周线KDJ+RSI+RPS20波段策略回测"""
    etf_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not etf_list:
        raise HTTPException(400, "请提供至少一个ETF代码")
    if len(etf_list) > 5:
        raise HTTPException(400, "最多支持5个ETF")

    results = []
    for code in etf_list:
        kdata = fetch_weekly(code, begin, end)
        if not kdata or len(kdata.get("closes", [])) < 30:
            results.append({"code": code, "error": f"无法获取{code}周线数据"})
            continue

        bt = run_band_backtest(kdata, {
            "buy_k": buy_k, "buy_rsi": buy_rsi, "buy_rps": buy_rps,
            "sell_k": sell_k, "sell_rsi": sell_rsi, "sell_rps": sell_rps,
            "initial_capital": initial_capital,
        })
        bt["code"] = code
        bt["label"] = code
        bt["strategy_params"] = {
            "buy_k": buy_k, "buy_rsi": buy_rsi, "buy_rps": buy_rps,
            "sell_k": sell_k, "sell_rsi": sell_rsi, "sell_rps": sell_rps,
        }
        bt["trade_summary"] = len(bt["trades"])
        bt.pop("trades", None)
        results.append(bt)

    base_params = {
        "buy_k": buy_k, "buy_rsi": buy_rsi, "buy_rps": buy_rps,
        "sell_k": sell_k, "sell_rsi": sell_rsi, "sell_rps": sell_rps,
        "initial_capital": initial_capital,
    }
    return JSONResponse({
        "mode": "band",
        "params": base_params,
        "period": f"{begin} ~ {end}",
        "results": results,
    })


@app.get("/api/backtest/rsi_trend")
async def backtest_rsi_trend(
    codes: str = Query(...),
    begin: str = Query("2021-01-01"),
    end: str = Query("2026-06-11"),
    rsi_buy: int = Query(50, description="RSI上穿此值买入"),
    rsi_sell: int = Query(40, description="RSI下穿此值卖出"),
    trail_stop: float = Query(10, description="移动止损百分比"),
    initial_capital: float = Query(1000000),
):
    """RSI趋势跟踪策略（周线）"""
    etf_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not etf_list:
        raise HTTPException(400, "请提供至少一个ETF代码")
    if len(etf_list) > 5:
        raise HTTPException(400, "最多5个ETF")

    results = []
    for code in etf_list:
        kdata = fetch_weekly(code, begin, end)
        if not kdata or len(kdata.get("closes", [])) < 30:
            results.append({"code": code, "error": f"无法获取{code}周线数据"})
            continue

        closes = kdata["closes"]
        rsi_vals = calc_rsi(closes)
        
        warmup = 20
        cap = initial_capital
        shares = 0
        in_pos = False
        highest = 0
        cost_basis = 0
        trades = []
        nav_series = [initial_capital] * warmup
        
        for i in range(warmup, len(closes)):
            p = closes[i]
            rv = rsi_vals[i] if i < len(rsi_vals) else None
            rv_prev = rsi_vals[i-1] if i > 0 and i-1 < len(rsi_vals) else None
            
            if rv is None:
                nav_series.append(cap + shares * p)
                continue
            
            if in_pos:
                if p > highest:
                    highest = p
                reason = None
                if rv < rsi_sell:
                    reason = f"RSI={rv:.0f}<{rsi_sell}"
                elif trail_stop > 0 and (highest - p) / highest * 100 >= trail_stop:
                    reason = f"移-{trail_stop}%"
                if reason:
                    proceeds = shares * p * (1 - 0.0003)
                    cap += proceeds
                    profit_pct = (p - cost_basis) / cost_basis * 100
                    trades.append({
                        "type": "sell", "idx": i, "price": round(p, 4),
                        "reason": reason, "profit_pct": round(profit_pct, 2)
                    })
                    shares = 0
                    in_pos = False
            
            if not in_pos:
                if rv_prev and rv > rsi_buy and rv_prev <= rsi_buy:
                    shares = int(cap / (p * (1 + 0.0003)))
                    cost = shares * p * (1 + 0.0003)
                    cap -= cost
                    cost_basis = p
                    highest = p
                    in_pos = True
                    trades.append({
                        "type": "buy", "idx": i, "price": round(p, 4),
                        "reason": f"RSI上穿{rv_prev:.0f}→{rv:.0f}>{rsi_buy}"
                    })
            
            nav_series.append(round(cap + shares * p, 2))
        
        if in_pos:
            p = closes[-1]
            cap += shares * p * (1 - 0.0003)
            trades.append({"type": "sell_final", "idx": len(closes)-1, "price": round(p, 4), "reason": "期末平仓"})
            nav_series[-1] = round(cap, 2)
        
        final_value = cap
        total_return = (final_value - initial_capital) / initial_capital * 100
        bh_return = (closes[-1] - closes[warmup]) / closes[warmup] * 100
        
        buys = [t for t in trades if t["type"] == "buy"]
        sells = [t for t in trades if "sell" in t["type"]]
        gains = []
        for b, s in zip(buys, sells):
            g = s.get("profit_pct", 0)
            if g == 0:
                g = (s["price"] - b["price"]) / b["price"] * 100
            gains.append(round(g, 2))
        
        peak = initial_capital
        max_dd = 0
        for nav in nav_series:
            if nav > peak: peak = nav
            dd = (peak - nav) / peak * 100
            max_dd = max(max_dd, dd)
        
        marks = [{"idx": t["idx"], "type": t["type"], "price": t["price"]} for t in trades]
        
        results.append({
            "code": code, "label": code,
            "total_return": round(total_return, 2),
            "buy_hold_return": round(bh_return, 2),
            "alpha": round(total_return - bh_return, 2),
            "trade_count": len(buys),
            "win_rate": round(sum(1 for g in gains if g > 0) / len(gains) * 100, 1) if gains else 0,
            "avg_gain": round(sum(gains)/len(gains), 2) if gains else 0,
            "worst_trade": round(min(gains), 2) if gains else 0,
            "max_drawdown": round(max_dd, 2),
            "skipped_volume": 0, "skipped_pause": 0,
            "sharpe_approx": round(sum(gains)/len(gains)/(__import__('statistics').stdev(gains) if len(gains)>1 else 1), 2) if gains and len(gains)>1 else 0,
            "gains": gains, "marks": marks, "trades": trades,
            "nav_series": nav_series, "closes": closes[warmup:], "min_days": warmup,
            "strategy_params": {"rsi_buy": rsi_buy, "rsi_sell": rsi_sell, "trail_stop": trail_stop},
        })
    
    base_params = {"rsi_buy": rsi_buy, "rsi_sell": rsi_sell, "trail_stop": trail_stop, "initial_capital": initial_capital}
    return JSONResponse({"mode": "rsi_trend", "params": base_params, "period": f"{begin} ~ {end}", "results": results})


@app.get("/api/backtest/detail")
async def backtest_detail(
    code: str = Query(...),
    begin: str = Query("2023-06-01"),
    end: str = Query("2026-06-11"),
    fast_ma: int = Query(5),
    mid_ma: int = Query(10),
    slow_ma: int = Query(20),
    hard_stop: float = Query(0),
    trail_stop: float = Query(0),
    initial_capital: float = Query(1000000),
    volume_confirm: float = Query(0),
    pause_after_losses: int = Query(0),
):
    """获取单个ETF的详细交易记录"""
    kdata = fetch_kline(code, begin, end)
    if not kdata or not kdata.get("closes"):
        raise HTTPException(404, "无法获取数据")
    
    params = {
        "fast_ma": fast_ma, "mid_ma": mid_ma, "slow_ma": slow_ma,
        "hard_stop": hard_stop, "trail_stop": trail_stop,
        "initial_capital": initial_capital,
        "volume_confirm": volume_confirm,
        "pause_after_losses": pause_after_losses,
    }
    
    bt = run_backtest(kdata, params)
    return JSONResponse(bt)


# ========== 申万行业ETF右侧轮动策略 ==========

INDUSTRY_ETF_CODES = [
    "515170.SH","516110.SH","512580.SH","512070.SH","515880.SH",
    "159997.SZ","512720.SH","159939.SZ","512010.SH","512800.SH",
    "515210.SH","515220.SH","512980.SH","512400.SH","512880.SH",
    "512670.SH","159996.SZ","159870.SZ","562510.SH","159707.SZ",
    "159825.SZ","159731.SZ","516910.SH","159745.SZ","516950.SH",
    "516160.SH","516960.SH",
]

BROAD_ETF_CODES = [
    "510300.SH",  # 沪深300ETF
    "513100.SH",  # 纳指ETF
    "518880.SH",  # 黄金ETF
    "511010.SH",  # 国债ETF
]

# 跨资产低相关宽基 (股+商品+债券)
CROSS_ASSET_CODES = [
    "159949.SZ",  # 创业板50ETF (A股成长)
    "515080.SH",  # 中证红利ETF (A股价值)
    "513100.SH",  # 纳指ETF (美股)
    "518880.SH",  # 黄金ETF (商品)
    "511010.SH",  # 国债ETF (债券)
]

ETF_POOLS = {
    "industry": INDUSTRY_ETF_CODES,
    "broad": BROAD_ETF_CODES,
    "cross_asset": CROSS_ASSET_CODES,
}

POOL_LABELS = {
    "industry": "申万一级行业 (27只)",
    "broad": "宽基指数 (4只)",
    "cross_asset": "跨资产低相关 (5只)",
}

INDUSTRY_DATA_DIR = os.path.expanduser("~/etf_backtest_data")


def load_industry_data(pool="industry"):
    """从CSV文件加载ETF日线数据, pool: 'industry' | 'broad'"""
    codes = ETF_POOLS.get(pool, INDUSTRY_ETF_CODES)
    dfs = {}
    for code in codes:
        fname = code.replace(".", "_") + ".csv"
        fpath = os.path.join(INDUSTRY_DATA_DIR, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f:
            first = f.readline().strip()
        has_header = "," in first and "date" in first.lower()
        
        dates, closes = [], []
        with open(fpath) as f:
            lines = f.readlines()
            start = 1 if has_header else 0
            for line in lines[start:]:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    dates.append(parts[0])
                    closes.append(float(parts[1]))
        if closes:
            dfs[code] = {"dates": dates, "closes": closes}
    return dfs


def run_industry_rotation(initial_capital, trail_stop, rebalance_weeks,
                          rsi_low, rsi_high, market_timing, dfs,
                          fast_ma=20, mid_ma=60, slow_ma=120,
                          max_positions=5, hard_stop=0, market_ma=50, etf_ma=0,
                          circuit_breaker=0, circuit_weeks=4):
    """运行行业轮动回测"""
    import math
    
    MA_SHORT, MA_MID, MA_LONG = fast_ma, mid_ma, slow_ma
    RSI_PERIOD = 14
    MOMENTUM_PERIOD = 20
    MAX_PER_ETF = initial_capital / max_positions if max_positions > 0 else 200000
    MAX_POSITIONS = max_positions
    
    # Build panel: dict[code] = {dates:[], closes:[], ma20:[], ma60:[], ma120:[], rsi:[], ret20:[]}
    panel = {}
    all_date_set = set()
    for code, data in dfs.items():
        closes = data["closes"]
        dates = data["dates"]
        n = len(closes)
        if n < MA_LONG + 30:
            continue
        
        # MA
        ma20 = [0.0] * n
        ma60 = [0.0] * n
        ma120 = [0.0] * n
        for i in range(n):
            if i >= MA_SHORT - 1:
                ma20[i] = sum(closes[i-MA_SHORT+1:i+1]) / MA_SHORT
            if i >= MA_MID - 1:
                ma60[i] = sum(closes[i-MA_MID+1:i+1]) / MA_MID
            if i >= MA_LONG - 1:
                ma120[i] = sum(closes[i-MA_LONG+1:i+1]) / MA_LONG
        
        # ETF自身长期MA过滤
        etf_mav = [0.0] * n
        if etf_ma > 0:
            for i in range(etf_ma - 1, n):
                etf_mav[i] = sum(closes[i-etf_ma+1:i+1]) / etf_ma
        
        # RSI(14) - Wilder smoothing
        rsi = [0.0] * n
        if n > RSI_PERIOD:
            gains, losses = [], []
            for i in range(1, RSI_PERIOD + 1):
                d = closes[i] - closes[i-1]
                gains.append(d if d > 0 else 0)
                losses.append(-d if d < 0 else 0)
            avg_gain = sum(gains) / RSI_PERIOD
            avg_loss = sum(losses) / RSI_PERIOD
            if avg_loss == 0:
                rsi[RSI_PERIOD] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi[RSI_PERIOD] = 100.0 - (100.0 / (1.0 + rs))
            
            for i in range(RSI_PERIOD + 1, n):
                d = closes[i] - closes[i-1]
                gain = d if d > 0 else 0
                loss = -d if d < 0 else 0
                avg_gain = (avg_gain * (RSI_PERIOD - 1) + gain) / RSI_PERIOD
                avg_loss = (avg_loss * (RSI_PERIOD - 1) + loss) / RSI_PERIOD
                if avg_loss == 0:
                    rsi[i] = 100.0
                else:
                    rs = avg_gain / avg_loss
                    rsi[i] = 100.0 - (100.0 / (1.0 + rs))
        
        # 20-day return
        ret20 = [0.0] * n
        for i in range(MOMENTUM_PERIOD, n):
            if closes[i-MOMENTUM_PERIOD] > 0:
                ret20[i] = (closes[i] - closes[i-MOMENTUM_PERIOD]) / closes[i-MOMENTUM_PERIOD]
        
        panel[code] = {
            "dates": dates, "closes": closes,
            "ma20": ma20, "ma60": ma60, "ma120": ma120,
            "etf_ma": etf_mav,
            "rsi": rsi, "ret20": ret20
        }
        all_date_set.update(dates)
    
    all_dates = sorted(all_date_set)
    date_to_idx = {d: i for i, d in enumerate(all_dates)}
    
    # Find start date (need MA120 warmup)
    earliest_ok = max(
        dfs[c]["dates"][min(MA_LONG, len(dfs[c]["dates"])-1)] 
        for c in panel if len(dfs[c]["dates"]) > MA_LONG
    )
    
    # Generate rebalance dates (every N Fridays)
    # Find first Friday after earliest_ok
    from datetime import datetime, timedelta
    start_dt = datetime.strptime(earliest_ok, "%Y%m%d")
    # Find next Friday
    days_until_fri = (4 - start_dt.weekday()) % 7
    first_fri = start_dt + timedelta(days=days_until_fri)
    
    rebalance_dates = []
    current = first_fri
    end_dt = datetime.strptime(all_dates[-1], "%Y%m%d")
    week_count = 0
    while current <= end_dt:
        date_str = current.strftime("%Y%m%d")
        if date_str in date_to_idx:
            if week_count % rebalance_weeks == 0:
                rebalance_dates.append(date_str)
            week_count += 1
        current += timedelta(days=7)
    
    rebalance_set = set(rebalance_dates)
    
    # Load market timing index (沪深300)
    market_data = None
    if market_timing:
        bm_path = os.path.join(INDUSTRY_DATA_DIR, "000300_SH.csv")
        if os.path.exists(bm_path):
            mkt_dates, mkt_closes = [], []
            with open(bm_path) as f:
                first = f.readline().strip()
                has_h = "," in first and "date" in first.lower()
                for line in (f.readlines() if has_h else [first] + f.readlines()):
                    parts = line.strip().split(",")
                    if len(parts) >= 2:
                        mkt_dates.append(parts[0])
                        mkt_closes.append(float(parts[1]))
            if has_h and first.strip():
                parts = first.strip().split(",")
                if len(parts) >= 2 and parts[0] != "date":
                    pass  # already read
            # Re-read from start
            mkt_dates, mkt_closes = [], []
            with open(bm_path) as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) >= 2:
                        try:
                            mkt_dates.append(parts[0])
                            mkt_closes.append(float(parts[1]))
                        except:
                            pass
            # Calculate market MA
            mkt_ma = [0.0] * len(mkt_closes)
            mkt_period = market_ma - 1
            for i in range(mkt_period, len(mkt_closes)):
                mkt_ma[i] = sum(mkt_closes[i-mkt_period:i+1]) / market_ma
            market_data = {"dates": mkt_dates, "closes": mkt_closes, "ma": mkt_ma, "period": market_ma}
    
    # Run simulation
    cash = initial_capital
    positions = {}  # code -> {shares, entry_idx, highest_close, cost}
    trades = []
    nav_series = []
    pos_count_series = []
    daily_dates = all_dates[date_to_idx[earliest_ok]:]
    
    # 组合熔断跟踪
    peak_nav = initial_capital
    circuit_cooldown = 0  # 剩余冷却周数
    cb_decimal = circuit_breaker / 100.0 if circuit_breaker > 0 else 0
    
    for date_str in daily_dates:
        idx = date_to_idx[date_str]
        
        # Check trailing stops
        codes_to_sell = []
        for code, pos in list(positions.items()):
            if code not in panel:
                continue
            pdata = panel[code]
            didx = pdata["dates"].index(date_str) if date_str in pdata["dates"] else -1
            if didx < 0:
                continue
            current_close = pdata["closes"][didx]
            if current_close > pos["highest_close"]:
                pos["highest_close"] = current_close
            # Trailing stop
            trail_stop_price = pos["highest_close"] * (1 - trail_stop)
            # Hard stop (from cost basis)
            hard_stop_hit = hard_stop > 0 and current_close <= pos.get("cost_basis", pos["cost"]/pos["shares"]) * (1 - hard_stop)
            if current_close <= trail_stop_price:
                codes_to_sell.append((code, current_close, f"移-{trail_stop*100:.0f}%"))
            elif hard_stop_hit:
                codes_to_sell.append((code, current_close, f"硬-{hard_stop*100:.0f}%"))
        
        for code, current_close, reason in codes_to_sell:
            pos = positions[code]
            proceeds = pos["shares"] * current_close
            pnl = proceeds - pos["cost"]
            pnl_pct = (pnl / pos["cost"] * 100) if pos["cost"] > 0 else 0
            cash += proceeds
            trades.append({"type": "sell", "code": code, "date": date_str,
                          "price": round(current_close, 4), "shares": pos["shares"],
                          "proceeds": round(proceeds, 2), "pnl": round(pnl, 2),
                          "pnl_pct": round(pnl_pct, 2),
                          "reason": reason})
            del positions[code]
        
        # Rebalance
        if date_str in rebalance_set:
            # 组合熔断冷却递减
            if circuit_cooldown > 0:
                circuit_cooldown -= 1
            
            # Market timing check
            market_bullish = True
            if market_data and date_str in market_data["dates"]:
                midx = market_data["dates"].index(date_str)
                if midx >= market_ma:
                    market_bullish = market_data["closes"][midx] > market_data["ma"][midx]
            
            # ---- Check MA death cross for existing positions ----
            codes_to_sell_ma = []
            for code, pos in list(positions.items()):
                pdata = panel.get(code)
                if not pdata:
                    continue
                didx = pdata["dates"].index(date_str) if date_str in pdata["dates"] else -1
                if didx < 1:
                    continue
                # MA fast cross below MA mid = 死叉卖出
                ma_fast_now = pdata["ma20"][didx]
                ma_mid_now = pdata["ma60"][didx]
                ma_fast_prev = pdata["ma20"][didx-1]
                ma_mid_prev = pdata["ma60"][didx-1]
                if (ma_fast_prev >= ma_mid_prev and ma_fast_now < ma_mid_now and
                    ma_fast_now > 0 and ma_mid_now > 0):
                    current_close = pdata["closes"][didx]
                    codes_to_sell_ma.append((code, current_close))
            
            for code, current_close in codes_to_sell_ma:
                pos = positions[code]
                proceeds = pos["shares"] * current_close
                pnl = proceeds - pos["cost"]
                pnl_pct = (pnl / pos["cost"] * 100) if pos["cost"] > 0 else 0
                cash += proceeds
                trades.append({"type": "sell", "code": code, "date": date_str,
                              "price": round(current_close, 4), "shares": pos["shares"],
                              "proceeds": round(proceeds, 2), "pnl": round(pnl, 2),
                              "pnl_pct": round(pnl_pct, 2),
                              "reason": "MA死叉"})
                del positions[code]
            
            # ---- Market turns bearish: sell all ----
            if not market_bullish:
                for code in list(positions.keys()):
                    pos = positions[code]
                    pdata = panel.get(code)
                    if not pdata:
                        continue
                    didx = pdata["dates"].index(date_str) if date_str in pdata["dates"] else -1
                    if didx < 0:
                        continue
                    current_close = pdata["closes"][didx]
                    proceeds = pos["shares"] * current_close
                    pnl = proceeds - pos["cost"]
                    pnl_pct = (pnl / pos["cost"] * 100) if pos["cost"] > 0 else 0
                    cash += proceeds
                    trades.append({"type": "sell", "code": code, "date": date_str,
                                  "price": round(current_close, 4), "shares": pos["shares"],
                                  "proceeds": round(proceeds, 2), "pnl": round(pnl, 2),
                                  "pnl_pct": round(pnl_pct, 2), "reason": "大盘转熊"})
                    del positions[code]
            
            # ---- Buy new positions (only if slots available & cash available) ----
            if market_bullish and len(positions) < MAX_POSITIONS and circuit_cooldown == 0:
                # Screen candidates (skip already-held ETFs)
                candidates = []
                for code in panel:
                    if code in positions:
                        continue  # 已持仓的不参与筛选
                    pdata = panel[code]
                    didx = pdata["dates"].index(date_str) if date_str in pdata["dates"] else -1
                    if didx < MA_LONG:
                        continue
                    c = pdata["closes"][didx]
                    ma20v = pdata["ma20"][didx]
                    ma60v = pdata["ma60"][didx]
                    ma120v = pdata["ma120"][didx]
                    rv = pdata["rsi"][didx]
                    rt = pdata["ret20"][didx]
                    
                    if ma20v > 0 and ma60v > 0 and ma120v > 0:
                        if (ma20v > ma60v > ma120v and c > ma20v and
                            rsi_low < rv < rsi_high and rt > 0):
                            # ETF自身长期MA过滤(价格必须在MA上方)
                            if etf_ma > 0:
                                etf_mav_val = pdata["etf_ma"][didx]
                                if etf_mav_val <= 0 or c <= etf_mav_val:
                                    continue
                            candidates.append((code, rt, c))
                
                candidates.sort(key=lambda x: x[1], reverse=True)
                
                # Buy top candidates until slots full or cash runs out
                slots = MAX_POSITIONS - len(positions)
                allocation_per = min(MAX_PER_ETF, cash / max(slots, 1))
                if allocation_per >= 10000:
                    for code, ret20, current_close in candidates[:slots]:
                        if code in positions:
                            continue
                        allocation = min(MAX_PER_ETF, allocation_per)
                        shares = int(allocation / current_close / 100) * 100
                        if shares == 0:
                            continue
                        cost = shares * current_close
                        if cost > cash:
                            continue
                        cash -= cost
                        positions[code] = {"shares": shares, "highest_close": current_close, "cost": cost, "cost_basis": current_close}
                        trades.append({"type": "buy", "code": code, "date": date_str,
                                      "price": round(current_close, 4), "shares": shares,
                                      "proceeds": round(cost, 2), "pnl": 0, "pnl_pct": 0,
                                      "reason": f"入选 ret20={ret20*100:.1f}%"})
        
        # Daily NAV
        pos_val = 0.0
        for code, pos in positions.items():
            pdata = panel.get(code)
            if pdata and date_str in pdata["dates"]:
                didx = pdata["dates"].index(date_str)
                pos_val += pos["shares"] * pdata["closes"][didx]
        total = cash + pos_val
        nav_series.append(round(total, 2))
        pos_count_series.append(len(positions))
        
        # 组合熔断检查
        if cb_decimal > 0 and circuit_cooldown == 0:
            if total > peak_nav:
                peak_nav = total
            dd_from_peak = (total - peak_nav) / peak_nav if peak_nav > 0 else 0
            if dd_from_peak <= -cb_decimal:
                # 触发熔断：清仓
                for code in list(positions.keys()):
                    pos = positions[code]
                    pdata = panel.get(code)
                    if not pdata or date_str not in pdata.get("dates", []):
                        continue
                    didx = pdata["dates"].index(date_str)
                    current_close = pdata["closes"][didx]
                    proceeds = pos["shares"] * current_close
                    pnl = proceeds - pos["cost"]
                    pnl_pct = (pnl / pos["cost"] * 100) if pos["cost"] > 0 else 0
                    cash += proceeds
                    trades.append({"type": "sell", "code": code, "date": date_str,
                                  "price": round(current_close, 4), "shares": pos["shares"],
                                  "proceeds": round(proceeds, 2), "pnl": round(pnl, 2),
                                  "pnl_pct": round(pnl_pct, 2),
                                  "reason": f"熔断-{circuit_breaker}%"})
                    del positions[code]
                circuit_cooldown = circuit_weeks
                peak_nav = total  # 重置峰值
    
    # Final liquidation
    if positions:
        last_date = daily_dates[-1]
        for code, pos in list(positions.items()):
            pdata = panel.get(code)
            if not pdata or last_date not in pdata["dates"]:
                continue
            didx = pdata["dates"].index(last_date)
            current_close = pdata["closes"][didx]
            proceeds = pos["shares"] * current_close
            pnl = proceeds - pos["cost"]
            pnl_pct = (pnl / pos["cost"] * 100) if pos["cost"] > 0 else 0
            cash += proceeds
            trades.append({"type": "sell", "code": code, "date": last_date,
                          "price": round(current_close, 4), "shares": pos["shares"],
                          "proceeds": round(proceeds, 2), "pnl": round(pnl, 2),
                          "pnl_pct": round(pnl_pct, 2), "reason": "回测结束"})
            del positions[code]
    
    # Stats
    final_value = nav_series[-1] if nav_series else initial_capital
    total_return = (final_value - initial_capital) / initial_capital * 100
    
    peak = nav_series[0]
    max_dd = 0.0
    for v in nav_series:
        if v > peak:
            peak = v
        dd = (v - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
    
    sells = [t for t in trades if t["type"] == "sell"]
    if sells:
        wins = sum(1 for t in sells if t["pnl"] > 0)
        win_rate = wins / len(sells) * 100
        avg_win = sum(t["pnl_pct"] for t in sells if t["pnl"] > 0) / wins if wins > 0 else 0
        avg_loss = sum(t["pnl_pct"] for t in sells if t["pnl"] <= 0) / (len(sells)-wins) if len(sells)-wins > 0 else 0
        total_pnl = sum(t["pnl"] for t in sells)
    else:
        win_rate = avg_win = avg_loss = total_pnl = 0
    
    return {
        "nav_series": nav_series,
        "daily_dates": daily_dates,
        "pos_count_series": pos_count_series,
        "trades": trades,
        "stats": {
            "final_value": round(final_value, 2),
            "total_return": round(total_return, 2),
            "max_drawdown": round(max_dd, 2),
            "num_trades": len(trades),
            "num_buys": len([t for t in trades if t["type"] == "buy"]),
            "num_sells": len(sells),
            "win_rate": round(win_rate, 1),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "total_pnl": round(total_pnl, 2),
            "initial_capital": initial_capital,
        },
    }


@app.get("/api/backtest/industry_rotation")
async def backtest_industry_rotation(
    pool: str = Query("industry", description="ETF池: industry | broad"),
    trail_stop: float = Query(8, description="移动止损百分比"),
    rebalance_weeks: int = Query(2, description="调仓周期间隔(周)"),
    rsi_low: int = Query(50, description="RSI下限"),
    rsi_high: int = Query(85, description="RSI上限"),
    market_timing: bool = Query(False, description="大盘择时(沪深300>MA200)"),
    market_ma: int = Query(50, description="大盘MA周期"),
    etf_ma: int = Query(0, description="ETF自身长期MA过滤(0=关闭)"),
    circuit_breaker: float = Query(0, description="组合熔断回撤阈值%(0=关闭)"),
    circuit_weeks: int = Query(4, description="熔断冷却周数"),
    initial_capital: float = Query(1000000),
    fast_ma: int = Query(20, description="快线周期"),
    mid_ma: int = Query(60, description="中线周期"),
    slow_ma: int = Query(120, description="慢线周期"),
    max_positions: int = Query(5, description="最大持仓数"),
    hard_stop: float = Query(0, description="硬止损%(0=关闭)"),
):
    """申万一级行业ETF右侧趋势轮动策略"""
    dfs = load_industry_data(pool)
    if not dfs:
        raise HTTPException(500, "无法加载行业ETF数据文件")
    
    trail_stop_decimal = trail_stop / 100.0
    hard_stop_decimal = hard_stop / 100.0
    
    result = run_industry_rotation(
        initial_capital, trail_stop_decimal, rebalance_weeks,
        rsi_low, rsi_high, market_timing, dfs,
        fast_ma=fast_ma, mid_ma=mid_ma, slow_ma=slow_ma,
        max_positions=max_positions,
        hard_stop=hard_stop_decimal,
        market_ma=market_ma,
        etf_ma=etf_ma,
        circuit_breaker=circuit_breaker,
        circuit_weeks=circuit_weeks,
    )
    
    return JSONResponse({
        "mode": "industry_rotation",
        "params": {
            "pool": pool,
            "trail_stop": trail_stop,
            "rebalance_weeks": rebalance_weeks,
            "rsi_low": rsi_low,
            "rsi_high": rsi_high,
            "market_timing": market_timing,
            "initial_capital": initial_capital,
            "fast_ma": fast_ma,
            "mid_ma": mid_ma,
            "slow_ma": slow_ma,
            "etf_ma": etf_ma,
        },
        "result": result,
    })


@app.get("/api/buy_timing")
async def buy_timing(
    code: str = Query(..., description="ETF代码,如 513120.SH"),
):
    """右侧买入时机分析 — 四维信号拆解"""
    end_date = datetime.now().strftime("%Y-%m-%d")
    begin_date = (datetime.now().replace(year=datetime.now().year - 2)).strftime("%Y-%m-%d")

    kline = fetch_kline(code, begin_date, end_date)
    if not kline or not kline.get("closes") or len(kline["closes"]) < 60:
        raise HTTPException(500, f"无法获取 {code} 的K线数据,或数据不足60天")

    closes = kline["closes"]
    dates = kline["dates"]
    n = len(closes)
    latest = closes[-1]
    latest_date = dates[-1]

    macd = calc_macd(closes)
    dif = macd["dif"]
    dea = macd["dea"]
    hist = macd["histogram"]

    macd_golden_cross = False
    cross_days_ago = None
    for i in range(n - 1, max(n - 20, 0), -1):
        if (dif[i] is not None and dea[i] is not None and
            dif[i-1] is not None and dea[i-1] is not None):
            if dif[i-1] <= dea[i-1] and dif[i] > dea[i]:
                macd_golden_cross = True
                cross_days_ago = n - 1 - i
                break

    macd_now_positive = dif[-1] is not None and dif[-1] > 0
    macd_converging = (dif[-1] is not None and dif[-5] is not None and
                       dif[-1] > dif[-5])

    rsi14 = calc_rsi(closes, 14)
    rsi_now = rsi14[-1] if rsi14[-1] is not None else 50.0
    rsi_healthy_range = 40 <= rsi_now <= 65
    rsi_oversold = rsi_now < 35
    rsi_overbought = rsi_now > 75
    rsi_20d_ago = rsi14[-20] if n >= 20 and rsi14[-20] is not None else rsi_now
    rsi_recovering = rsi_now > rsi_20d_ago and rsi_20d_ago < 50

    low_52w = find_52w_low(closes)
    dist_from_low = (latest - low_52w) / low_52w * 100
    low_60d = find_recent_low(closes, 60)
    double_bottom = False
    if dist_from_low > 3 and dist_from_low < 15:
        for i in range(max(n - 60, 0), n - 5):
            if closes[i] <= low_52w * 1.03:
                double_bottom = True
                break
    bottom_confirmed = double_bottom or (rsi_recovering and dist_from_low > 5)

    ma20 = calc_sma(closes, 20)
    ma60 = calc_sma(closes, 60)
    ma120 = calc_sma(closes, 120)
    ma20_now = ma20[-1] if ma20[-1] is not None else 0.0
    ma60_now = ma60[-1] if ma60[-1] is not None else 0.0
    ma20_slope = 0.0
    ma20_slope_5d_ago = 0.0
    if ma20[-1] is not None and ma20[-6] is not None:
        ma20_slope = (ma20[-1] - ma20[-6]) / ma20[-6] * 100
    if ma20[-6] is not None and ma20[-11] is not None:
        ma20_slope_5d_ago = (ma20[-6] - ma20[-11]) / ma20[-11] * 100
    ma_flattening = abs(ma20_slope) < 1.0
    ma_turning_up = ma20_slope > ma20_slope_5d_ago and ma20_slope > -0.5
    above_ma20 = latest > ma20_now
    above_ma60 = latest > ma60_now
    ma20_above_ma60 = ma20_now > ma60_now

    signals = {
        "macd_golden_cross": macd_golden_cross,
        "macd_positive": macd_now_positive,
        "macd_converging": macd_converging,
        "cross_days_ago": cross_days_ago,
        "rsi_now": round(rsi_now, 1),
        "rsi_healthy": rsi_healthy_range,
        "rsi_oversold": rsi_oversold,
        "rsi_overbought": rsi_overbought,
        "rsi_recovering": rsi_recovering,
        "bottom_confirmed": bottom_confirmed,
        "double_bottom": double_bottom,
        "dist_from_52w_low": round(dist_from_low, 1),
        "low_52w": round(low_52w, 2),
        "ma20_slope": round(ma20_slope, 2),
        "ma_flattening": ma_flattening,
        "ma_turning_up": ma_turning_up,
        "above_ma20": above_ma20,
        "above_ma60": above_ma60,
        "ma20_above_ma60": ma20_above_ma60,
    }

    score = 0
    if macd_golden_cross:
        detail_macd = "\u2705 MACD已金叉，中期趋势转多信号"
        score += 25
    elif macd_converging and not macd_now_positive:
        detail_macd = "\u26a0\ufe0f MACD尚未金叉，但DIF在零轴下方收窄（筑底中）"
        score += 10
    elif macd_now_positive:
        detail_macd = "\u2705 MACD在零轴上方运行，多头趋势延续中"
        score += 20
    else:
        detail_macd = "\u274c MACD零轴下方且未收敛，空头趋势中"

    if rsi_healthy_range and rsi_recovering:
        detail_rsi = "\u2705 RSI在40-65健康区间，且从低位回升，动能恢复中"
        score += 25
    elif rsi_healthy_range:
        detail_rsi = "\u2705 RSI在40-65健康区间（中性偏强）"
        score += 20
    elif rsi_oversold:
        detail_rsi = "\u26a0\ufe0f RSI<35超卖区，可能有反弹但需等趋势确认（不抄底）"
        score += 10
    elif rsi_overbought:
        detail_rsi = "\u26a0\ufe0f RSI>75超买区，短期追高风险较大，等回调再入"
        score += 5
    elif rsi_now > 65:
        detail_rsi = "\u26a0\ufe0f RSI偏强(>65)，接近超买，等回调到50-60区间更安全"
        score += 12
    else:
        detail_rsi = "\u274c RSI偏弱，暂无买入信号"

    if bottom_confirmed and dist_from_low > 5:
        detail_bottom = f"\u2705 已从52周低点反弹+{dist_from_low:.0f}%且二次探底确认，底部扎实"
        score += 25
    elif bottom_confirmed:
        detail_bottom = f"\u2705 有二次探底确认信号，前低{low_52w:.2f}已受考验"
        score += 20
    elif dist_from_low < 5:
        detail_bottom = f"\u26a0\ufe0f 距52周低点仅+{dist_from_low:.0f}%，单底反弹未确认，需等回踩"
        score += 8
    elif dist_from_low > 15:
        detail_bottom = f"\u26a0\ufe0f 已从低点反弹+{dist_from_low:.0f}%，追入性价比降低"
        score += 10
    else:
        detail_bottom = "\u274c 无明显底部形态"

    if above_ma20 and above_ma60 and ma20_above_ma60 and ma_turning_up:
        detail_ma = "\u2705 价格站上MA20/MA60，MA20上穿MA60且拐头向上，多头排列形成中"
        score += 25
    elif above_ma20 and above_ma60 and ma20_above_ma60:
        detail_ma = "\u2705 价格在MA20/MA60上方，MA20>MA60，趋势向好"
        score += 20
    elif above_ma20 and ma_turning_up:
        detail_ma = "\u26a0\ufe0f 价格站上MA20且MA20开始拐头，但MA60仍在压制"
        score += 12
    elif ma_flattening:
        detail_ma = "\u26a0\ufe0f MA20正在走平（筑底特征），等待拐头确认"
        score += 8
    else:
        detail_ma = "\u274c 均线空头排列，MA20/MA60向下，趋势未转多"

    if score >= 80:
        verdict = "\U0001f7e2 右侧信号较强，可考虑入场（建议分批建仓+移动止损）"
    elif score >= 55:
        verdict = "\U0001f7e1 部分右侧信号出现，但条件不够完整，建议等待更多信号确认"
    elif score >= 30:
        verdict = "\U0001f7e0 右侧信号偏弱，仅有零星积极信号，继续观望"
    else:
        verdict = "\U0001f534 右侧信号缺失，空头趋势明显，不建议买入"

    chart_len = min(250, n)
    chart_data = {
        "dates": dates[-chart_len:],
        "closes": closes[-chart_len:],
        "ma20": [round(v, 3) if v is not None else None for v in ma20[-chart_len:]],
        "ma60": [round(v, 3) if v is not None else None for v in ma60[-chart_len:]],
        "ma120": [round(v, 3) if v is not None else None for v in ma120[-chart_len:]],
        "macd_dif": [round(v, 4) if v is not None else None for v in dif[-chart_len:]],
        "macd_dea": [round(v, 4) if v is not None else None for v in dea[-chart_len:]],
        "macd_hist": [round(v, 4) if v is not None else None for v in hist[-chart_len:]],
        "rsi": [round(v, 1) if v is not None else None for v in rsi14[-chart_len:]],
    }

    return JSONResponse({
        "code": code,
        "latest_price": round(latest, 3),
        "latest_date": latest_date,
        "signals": signals,
        "score": score,
        "details": {
            "macd": detail_macd,
            "rsi": detail_rsi,
            "bottom": detail_bottom,
            "ma": detail_ma,
        },
        "verdict": verdict,
        "chart": chart_data,
    })


# 静态文件
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8899)
