"""诊断+回测 - 多组阈值对比"""
import json, subprocess, os
from band_backtest import fetch_weekly, calc_kdj, calc_rsi, calc_rps20

data = fetch_weekly("159995.SZ", "2021-01-01", "2026-06-11")
closes = data["closes"]
highs = data["highs"]
lows = data["lows"]

K, D, J = calc_kdj(highs, lows, closes)
rsi = calc_rsi(closes)
rps = calc_rps20(closes)

warmup = 20

def backtest(buy_k, buy_rsi, buy_rps, sell_k, sell_rsi, sell_rps):
    """买入: K<buy_k AND RSI<buy_rsi AND RPS>=buy_rps
       卖出: K>sell_k OR RSI>sell_rsi OR RPS<sell_rps"""
    cap = 1000000
    shares = 0
    in_pos = False
    cost_basis = 0
    trades = []
    
    for i in range(warmup, len(closes)):
        p = closes[i]
        kv, rv, pv = K[i], rsi[i], rps[i]
        if None in (kv, rv, pv):
            continue
        
        if in_pos:
            reason = None
            if kv > sell_k: reason = f"K>{sell_k}"
            elif rv > sell_rsi: reason = f"RSI>{sell_rsi}"
            elif pv < sell_rps: reason = f"RPS<{sell_rps}"
            if reason:
                cap += shares * p * 0.9997
                shares = 0
                in_pos = False
                trades.append(("sell", i, p, reason))
        
        if not in_pos:
            if kv < buy_k and rv < buy_rsi and pv >= buy_rps:
                shares = int(cap / (p * 1.0003))
                cap -= shares * p * 1.0003
                cost_basis = p
                in_pos = True
                trades.append(("buy", i, p, f"K={kv:.0f} RSI={rv:.0f}"))
    
    if in_pos:
        cap += shares * closes[-1] * 0.9997
        trades.append(("sell", len(closes)-1, closes[-1], "期末"))
    
    ret = (cap - 1000000) / 10000
    bh = (closes[-1] - closes[warmup]) / closes[warmup] * 100
    buys = sum(1 for t in trades if t[0]=='buy')
    
    # 计算胜率
    gains = []
    for j in range(0, len(trades)-1, 2):
        if trades[j][0]=='buy' and trades[j+1][0].startswith('sell'):
            g = (trades[j+1][2] - trades[j][2]) / trades[j][2] * 100
            gains.append(g)
    
    wr = sum(1 for g in gains if g>0)/len(gains)*100 if gains else 0
    
    return ret, round(bh, 1), buys, round(wr, 1), len(gains)

configs = [
    # (buy_k, buy_rsi, buy_rps, sell_k, sell_rsi, sell_rps)
    ("原始", 30, 30, 10, 90, 90, 30),
    ("放宽B1", 30, 40, 10, 80, 70, 20),
    ("放宽B2", 35, 40, 10, 80, 70, 20),
    ("宽松B3", 40, 45, 10, 80, 70, 20),
    ("保守S1", 30, 40, 10, 70, 65, 15),
    ("均衡",   35, 40, 10, 75, 70, 20),
    ("更保守B", 25, 35, 15, 80, 70, 25),
]

print(f"{'阈值组':<12} {'收益%':>8} {'持有%':>8} {'交易':>5} {'胜率%':>7} {'笔数':>5}")
print("-"*50)
bh_all = (closes[-1] - closes[warmup]) / closes[warmup] * 100
for name, bk, br, bp, sk, sr, sp in configs:
    ret, bh, tr, wr, cnt = backtest(bk, br, bp, sk, sr, sp)
    print(f"{name:<12} {ret:>+7.1f}% {bh:>+7.1f}% {tr:>5} {wr:>6.1f}% {cnt:>5}")
print(f"{'买入持有':<12} {bh_all:>+7.1f}%")
