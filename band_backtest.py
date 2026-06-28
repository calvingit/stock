"""
波段交易策略回测 - 周线 KDJ + RSI + RPS20
"""
import json
import subprocess
import os
from datetime import datetime

WIND_CLI_DIR = os.path.expanduser("~/.hermes/skills/wind-mcp-skill")
CACHE_DIR = "/tmp/etf_backtest_cache"

def fetch_weekly(etf_code: str, begin: str, end: str) -> dict:
    """获取周线数据"""
    cache_key = f"w_{etf_code}_{begin}_{end}"
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    if os.path.exists(cache_file):
        age = datetime.now().timestamp() - os.path.getmtime(cache_file)
        if age < 86400:
            with open(cache_file) as f:
                return json.load(f)
    
    cmd = [
        "node", "scripts/cli.mjs", "call", "fund_data", "get_fund_kline",
        json.dumps({
            "windcode": etf_code,
            "begin_date": begin.replace("-", ""),
            "end_date": end.replace("-", ""),
            "period": "11"  # 周K
        })
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=WIND_CLI_DIR)
    if result.returncode != 0:
        return {}
    
    outer = json.loads(result.stdout)
    inner = json.loads(outer["content"][0]["text"])
    if inner.get("error"):
        return {}
    
    rows = inner["data"]["rows"]
    # cols: TIME, OPEN, MATCH(close), HIGH, LOW, TURNOVER, VOLUME, CHANGEHANDRATE, AVPRICE, _DATE
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


def calc_kdj(highs, lows, closes, n=9):
    """计算KDJ(9,3,3)"""
    K, D, J = [], [], []
    prev_k, prev_d = 50.0, 50.0
    
    for i in range(len(closes)):
        if i < n - 1:
            K.append(None)
            D.append(None)
            J.append(None)
            continue
        
        h = max(highs[i-n+1:i+1])
        l = min(lows[i-n+1:i+1])
        rsv = (closes[i] - l) / (h - l) * 100 if h != l else 50
        
        k_val = 2/3 * prev_k + 1/3 * rsv
        d_val = 2/3 * prev_d + 1/3 * k_val
        j_val = 3 * k_val - 2 * d_val
        
        K.append(round(k_val, 2))
        D.append(round(d_val, 2))
        J.append(round(j_val, 2))
        prev_k, prev_d = k_val, d_val
    
    return K, D, J


def calc_rsi(closes, n=14):
    """计算 RSI(14)"""
    rsi = [None] * n
    gains, losses = [], []
    
    for i in range(1, n + 1):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    
    avg_gain = sum(gains) / n
    avg_loss = sum(losses) / n
    
    rsi.append(round(100 - 100/(1 + avg_gain/avg_loss), 2) if avg_loss > 0 else 100.0)
    
    for i in range(n + 1, len(closes)):
        diff = closes[i] - closes[i-1]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        avg_gain = (avg_gain * (n-1) + gain) / n
        avg_loss = (avg_loss * (n-1) + loss) / n
        rsi.append(round(100 - 100/(1 + avg_gain/avg_loss), 2) if avg_loss > 0 else 100.0)
    
    return rsi


def calc_rps20(closes):
    """RPS20: 20周涨跌幅的百分位排名(0-100)"""
    ret_20w = []
    for i in range(len(closes)):
        if i < 20:
            ret_20w.append(None)
        else:
            ret_20w.append((closes[i] - closes[i-20]) / closes[i-20] * 100)
    
    # 百分位排名：当前值在历史所有值中的分位
    rps = [None] * len(closes)
    all_rets = [r for r in ret_20w if r is not None]
    
    for i in range(len(closes)):
        if ret_20w[i] is None:
            continue
        # 排名：比当前值小的占比 * 100
        rank = sum(1 for r in all_rets if r < ret_20w[i]) / len(all_rets) * 100
        rps[i] = round(rank, 2)
    
    return rps


def run_band_backtest(data: dict, initial=1000000):
    """
    波段交易策略回测
    买入：KDJ_K < 30 AND RSI < 30 AND RPS20 >= 10
    卖出：KDJ_K > 90 OR RSI > 90 OR RPS20 < 30
    """
    closes = data["closes"]
    highs = data["highs"]
    lows = data["lows"]
    dates = data["dates"]
    
    K, D, J = calc_kdj(highs, lows, closes)
    rsi = calc_rsi(closes)
    rps = calc_rps20(closes)
    
    warmup = 20  # 至少需要20周数据
    
    cap = initial
    shares = 0
    in_pos = False
    cost_basis = 0
    trades = []
    
    nav_series = [initial] * warmup
    
    for i in range(warmup, len(closes)):
        p = closes[i]
        k_val = K[i]
        rsi_val = rsi[i]
        rps_val = rps[i]
        
        if None in (k_val, rsi_val, rps_val):
            nav_series.append(cap + shares * p)
            continue
        
        # 卖出判断
        if in_pos:
            sell_reason = None
            if k_val > 90:
                sell_reason = f"KDJ_K={k_val:.0f}>90"
            elif rsi_val > 90:
                sell_reason = f"RSI={rsi_val:.0f}>90"
            elif rps_val < 30:
                sell_reason = f"RPS20={rps_val:.0f}<30"
            
            if sell_reason:
                proceeds = shares * p * 0.9997
                cap += proceeds
                profit_pct = (proceeds - shares * cost_basis * 1.0003) / (shares * cost_basis) * 100
                trades.append({
                    "type": "sell", "idx": i, "price": round(p, 4),
                    "reason": sell_reason, "profit_pct": round(profit_pct, 2)
                })
                shares = 0
                in_pos = False
        
        # 买入判断
        if not in_pos:
            if k_val < 30 and rsi_val < 30 and rps_val >= 10:
                shares = int(cap / (p * 1.0003))
                cost = shares * p * 1.0003
                cap -= cost
                cost_basis = p
                in_pos = True
                trades.append({
                    "type": "buy", "idx": i, "price": round(p, 4),
                    "reason": f"K={k_val:.0f} RSI={rsi_val:.0f} RPS={rps_val:.0f}"
                })
        
        nav_series.append(round(cap + shares * p, 2))
    
    # 期末平仓
    if in_pos:
        p = closes[-1]
        cap += shares * p * 0.9997
        trades.append({"type": "sell_final", "idx": len(closes)-1, "price": round(p, 4), "reason": "期末平仓"})
        nav_series[-1] = round(cap, 2)
    
    final_value = cap
    total_return = (final_value - initial) / initial * 100
    
    buys = [t for t in trades if t["type"] == "buy"]
    sells = [t for t in trades if "sell" in t["type"]]
    
    gains = []
    for b, s in zip(buys, sells):
        g = (s.get("profit_pct", 0)) if "profit_pct" in s else 0
        if not g:
            proceeds = s.get("price", 0) * b.get("shares", 0) * 0.9997 if isinstance(s, dict) else 0
            cost = b.get("price", 0) * b.get("shares", 0) * 1.0003 if isinstance(b, dict) else 0
            g = (proceeds - cost) / cost * 100 if cost else 0
        gains.append(round(g, 2))
    
    # 计算收益
    for j, (b, s) in enumerate(zip(buys, sells)):
        if j < len(gains) and gains[j] == 0:
            proceeds = s["price"] * 100 * 0.9997  # approx
            cost = b["price"] * 100 * 1.0003
            gains[j] = round((proceeds - cost) / cost * 100, 2)
    
    # 最大回撤
    peak = initial
    max_dd = 0
    for nav in nav_series:
        if nav > peak:
            peak = nav
        dd = (peak - nav) / peak * 100
        max_dd = max(max_dd, dd)
    
    # 买入持有
    bh_return = (closes[-1] - closes[warmup]) / closes[warmup] * 100
    
    return {
        "total_return": round(total_return, 2),
        "buy_hold_return": round(bh_return, 2),
        "alpha": round(total_return - bh_return, 2),
        "trade_count": len(buys),
        "win_rate": round(sum(1 for g in gains if g > 0) / len(gains) * 100, 1) if gains else 0,
        "avg_gain": round(sum(gains)/len(gains), 2) if gains else 0,
        "worst_trade": round(min(gains), 2) if gains else 0,
        "max_drawdown": round(max_dd, 2),
        "trades": trades,
        "gains": gains,
        "nav_series": nav_series,
        "closes": closes[warmup:],
        "min_days": warmup,
        "kdj_k": K,
        "rsi": rsi,
        "rps20": rps,
    }


if __name__ == "__main__":
    print("获取159995.SZ周线数据...")
    data = fetch_weekly("159995.SZ", "2021-01-01", "2026-06-11")
    print(f"数据: {len(data['closes'])} 周")
    
    result = run_band_backtest(data)
    
    print(f"\n=== 芯片ETF波段策略回测 ===")
    print(f"策略收益: {result['total_return']:+.2f}%")
    print(f"买入持有: {result['buy_hold_return']:+.2f}%")
    print(f"超额α:   {result['alpha']:+.2f}%")
    print(f"交易次数: {result['trade_count']}轮")
    print(f"胜率:     {result['win_rate']}%")
    print(f"组合回撤: {result['max_drawdown']:.2f}%")
    print(f"单笔最差: {result['worst_trade']:+.2f}%")
    print(f"均笔收益: {result['avg_gain']:+.2f}%")
    
    print(f"\n最近10条交易:")
    for t in result['trades'][-10:]:
        print(f"  {t['type']:10s} @ {t['price']:.3f}  {t.get('reason','')}")
    
    # 输出最近指标
    print(f"\n当前指标:")
    print(f"  KDJ_K: {result['kdj_k'][-1]}")
    print(f"  RSI:   {result['rsi'][-1]}")
    print(f"  RPS20: {result['rps20'][-1]}")
