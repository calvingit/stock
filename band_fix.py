"""测试去掉RPS20卖出条件"""
import json

cache_file = "/tmp/etf_backtest_cache/w_159995.SZ_2021-01-01_2026-06-11.json"
with open(cache_file) as f:
    data = json.load(f)

from band_backtest import calc_kdj, calc_rsi, calc_rps20

closes, highs, lows = data['closes'], data['highs'], data['lows']
K, _, _ = calc_kdj(highs, lows, closes)
rsi = calc_rsi(closes)
rps = calc_rps20(closes)

def run(bk, br, bp, sk, sr, sp, use_rps_sell):
    warmup, cap, shares, in_pos = 20, 1000000, 0, False
    trades = []
    for i in range(warmup, len(closes)):
        p, kv, rv, pv = closes[i], K[i], rsi[i], rps[i]
        if None in (kv, rv, pv): continue
        if in_pos:
            reason = None
            if kv > sk: reason = f"KDJ_K={kv:.0f}>{sk}"
            elif rv > sr: reason = f"RSI={rv:.0f}>{sr}"
            elif use_rps_sell and pv < sp: reason = f"RPS20={pv:.0f}<{sp}"
            if reason:
                cap += shares * p * 0.9997; shares = 0; in_pos = False
                trades.append(("sell", i, p, reason))
        if not in_pos:
            if kv < bk and rv < br and pv >= bp:
                shares = int(cap/(p*1.0003)); cap -= shares*p*1.0003; in_pos = True
                trades.append(("buy", i, p, f"K={kv:.0f} RSI={rv:.0f}"))
    if in_pos:
        cap += shares * closes[-1] * 0.9997
        trades.append(("sell", len(closes)-1, closes[-1], "期末"))
    
    ret = (cap-1000000)/10000
    bh = (closes[-1]-closes[warmup])/closes[warmup]*100
    buys = sum(1 for t in trades if t[0]=='buy')
    
    gains = []
    for j in range(0, len(trades)-1, 2):
        if trades[j][0]=='buy' and trades[j+1][0].startswith('sell'):
            gains.append((trades[j+1][2]-trades[j][2])/trades[j][2]*100)
    wr = sum(1 for g in gains if g>0)/len(gains)*100 if gains else 0
    
    return ret, bh, buys, wr

print(f"{'配置':<35} {'收益%':>7} {'持有%':>7} {'交易':>5} {'胜率':>6}")
print("-"*65)

# 原始
r = run(30,40,10,80,70,20, True)
print(f"{'原始(K<30,RSI<40,RPS<20卖出)':<35} {r[0]:>+6.1f}% {r[1]:>+6.1f}% {r[2]:>5} {r[3]:>5.1f}%")

# 去掉RPS20卖出
r = run(30,40,10,80,70,999, False)
print(f"{'去掉RPS卖出(只用KDJ/RSI)':<35} {r[0]:>+6.1f}% {r[1]:>+6.1f}% {r[2]:>5} {r[3]:>5.1f}%")

# 放宽买入+去掉RPS卖出
r = run(35,45,10,80,70,999, False)
print(f"{'放宽买入+去掉RPS卖出':<35} {r[0]:>+6.1f}% {r[1]:>+6.1f}% {r[2]:>5} {r[3]:>5.1f}%")

# 更宽松
r = run(40,45,10,80,70,999, False)
print(f"{'宽松买入+去掉RPS卖出':<35} {r[0]:>+6.1f}% {r[1]:>+6.1f}% {r[2]:>5} {r[3]:>5.1f}%")

# 买入持有
bh = (closes[-1]-closes[20])/closes[20]*100
print(f"{'买入持有':<35} {bh:>+6.1f}%")
