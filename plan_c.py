"""
方案C: 保留KDJ+RSI+RPS20买入信号, 卖出改成移动止损
"""
import json

cache_file = "/tmp/etf_backtest_cache/w_159995.SZ_2021-01-01_2026-06-11.json"
with open(cache_file) as f:
    data = json.load(f)

from band_backtest import calc_kdj, calc_rsi, calc_rps20

closes, highs, lows = data['closes'], data['highs'], data['lows']
K, _, _ = calc_kdj(highs, lows, closes)
rsi = calc_rsi(closes)
rps = calc_rps20(closes)

def run(bk, br, bp, trail_pct):
    """买入: K<bk, RSI<br, RPS>=bp; 卖出: 从最高点回撤trail_pct%"""
    warmup, cap, shares, in_pos = 20, 1000000, 0, False
    highest, cost_basis = 0, 0
    trades, nav = [], [cap]*warmup
    
    for i in range(warmup, len(closes)):
        p, kv, rv, pv = closes[i], K[i], rsi[i], rps[i]
        if None in (kv, rv, pv):
            nav.append(cap + shares*p); continue
        
        if in_pos:
            if p > highest: highest = p
            # 移动止损
            dd = (highest - p) / highest * 100
            if dd >= trail_pct:
                cap += shares * p * 0.9997
                profit = (p - cost_basis) / cost_basis * 100
                trades.append((f"卖", i, p, f"回撤{dd:.1f}%≥{trail_pct}% 盈亏{profit:+.1f}%"))
                shares = 0; in_pos = False
        
        if not in_pos:
            if kv < bk and rv < br and pv >= bp:
                shares = int(cap/(p*1.0003)); cap -= shares*p*1.0003
                cost_basis = p; highest = p; in_pos = True
                trades.append(("买", i, p, f"K={kv:.0f} RSI={rv:.0f} RPS={pv:.0f}"))
        
        nav.append(cap + shares*p)
    
    if in_pos:
        cap += shares * closes[-1] * 0.9997
        trades.append(("卖", len(closes)-1, closes[-1], "期末"))
        nav[-1] = cap
    
    ret = (cap - 1000000) / 10000
    bh = (closes[-1] - closes[warmup]) / closes[warmup] * 100
    
    buys = sum(1 for t in trades if t[0]=='买')
    gains = []
    for j in range(0, len(trades)-1, 2):
        if j+1 < len(trades) and trades[j][0]=='买':
            gains.append((trades[j+1][2]-trades[j][2])/trades[j][2]*100)
    wr = sum(1 for g in gains if g>0)/len(gains)*100 if gains else 0
    
    # 最大回撤
    peak = 1000000; max_dd = 0
    for v in nav:
        if v > peak: peak = v
        dd = (peak-v)/peak*100
        if dd > max_dd: max_dd = dd
    
    return ret, bh, buys, wr, round(max_dd,1), gains

print(f"{'策略':<30} {'收益%':>7} {'持有%':>7} {'交易':>5} {'胜率':>6} {'最大回撤':>8}")
print("-"*70)
bh = run(30,40,10,0)[1]  # just get bh

# 原始指标卖出
r = run(30,40,10,0)  # trail=0 means no trailing stop - will hold forever, use this as baseline

# 不同移动止损
for trail in [5, 8, 10, 12, 15, 20]:
    r = run(30, 40, 10, trail)
    print(f"买入K<30,RSI<40 + 移{trail}%止损{'':<12} {r[0]:>+6.1f}% {r[1]:>+6.1f}% {r[2]:>5} {r[3]:>5.1f}% {r[4]:>7.1f}%")

print(f"\n买入持有{'':<22} {bh:>+6.1f}%")

# 看看放宽买入+移损
print(f"\n--- 放宽买入 ---")
for bk,br in [(35,45),(30,45),(35,40)]:
    for trail in [8,10,12]:
        r = run(bk, br, 10, trail)
        if r[2] > 1:
            print(f"K<{bk},RSI<{br} + 移{trail}%{'':<12} {r[0]:>+6.1f}% {r[1]:>+6.1f}% {r[2]:>5} {r[3]:>5.1f}% {r[4]:>7.1f}%")

# 最佳组合的详细交易
print(f"\n=== 最佳组合: K<30,RSI<40 + 移10%止损 ===")
trades, nav = [], []
cap, shares, in_pos = 1000000, 0, False
highest, cost_basis = 0, 0
for i in range(20, len(closes)):
    p, kv, rv, pv = closes[i], K[i], rsi[i], rps[i]
    if None in (kv, rv, pv):
        nav.append(cap+shares*p); continue
    if in_pos:
        if p > highest: highest = p
        if (highest-p)/highest*100 >= 10:
            cap += shares*p*0.9997
            profit = (p-cost_basis)/cost_basis*100
            trades.append(("卖",i,p,f"盈亏{profit:+.1f}%"))
            shares=0;in_pos=False
    if not in_pos:
        if kv<30 and rv<40 and pv>=10:
            shares=int(cap/(p*1.0003));cap-=shares*p*1.0003
            cost_basis=p;highest=p;in_pos=True
            trades.append(("买",i,p,""))
    nav.append(cap+shares*p)

buys = [t for t in trades if t[0]=='买']
sells = [t for t in trades if t[0]=='卖']
for i,(b,s) in enumerate(zip(buys,sells)):
    held = s[1]-b[1]
    ret = (s[2]-b[2])/b[2]*100
    print(f"#{i+1}: 买¥{b[2]:.3f}→卖¥{s[2]:.3f} 持{held}周 {ret:+.1f}% | {s[3]}")
