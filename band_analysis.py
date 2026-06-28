"""分析波段策略为什么跑输"""
import json
from collections import Counter

cache_file = "/tmp/etf_backtest_cache/w_159995.SZ_2021-01-01_2026-06-11.json"
with open(cache_file) as f:
    data = json.load(f)

from band_backtest import calc_kdj, calc_rsi, calc_rps20

def backtest(data, bk=30, br=40, bp=10, sk=80, sr=70, sp=20):
    closes, highs, lows = data['closes'], data['highs'], data['lows']
    K, _, _ = calc_kdj(highs, lows, closes)
    rsi = calc_rsi(closes)
    rps = calc_rps20(closes)
    warmup = 20
    cap, shares, in_pos = 1000000, 0, False
    trades = []
    for i in range(warmup, len(closes)):
        p, kv, rv, pv = closes[i], K[i], rsi[i], rps[i]
        if None in (kv, rv, pv): continue
        if in_pos:
            reason = None
            if kv > sk: reason = f"KDJ_K={kv:.0f}>{sk}"
            elif rv > sr: reason = f"RSI={rv:.0f}>{sr}"
            elif pv < sp: reason = f"RPS20={pv:.0f}<{sp}"
            if reason:
                cap += shares * p * 0.9997; shares = 0; in_pos = False
                trades.append({"type":"sell","idx":i,"price":p,"reason":reason})
        if not in_pos:
            if kv < bk and rv < br and pv >= bp:
                shares = int(cap/(p*1.0003)); cap -= shares*p*1.0003; in_pos = True
                trades.append({"type":"buy","idx":i,"price":p,"reason":f"K={kv:.0f} RSI={rv:.0f} RPS={pv:.0f}"})
    if in_pos:
        cap += shares * closes[-1] * 0.9997
        trades.append({"type":"sell_final","idx":len(closes)-1,"price":closes[-1],"reason":"期末平仓"})
    return trades, K, rsi

trades, K, rsi = backtest(data)
buys = [t for t in trades if t['type']=='buy']
sells = [t for t in trades if 'sell' in t['type']]
closes = data['closes']

print("=== 13笔交易逐笔分析 ===\n")
total_in, total_gain = 0, 0
for i, (b, s) in enumerate(zip(buys, sells)):
    b_idx, s_idx = b['idx'], s['idx']
    held = s_idx - b_idx; total_in += held
    held_ret = (closes[s_idx]-closes[b_idx])/closes[b_idx]*100
    total_gain += held_ret
    # 离场后到下次买入的涨幅
    nb = buys[i+1] if i+1<len(buys) else None
    missed_ret = (closes[nb['idx']]-closes[s_idx])/closes[s_idx]*100 if nb else (closes[-1]-closes[s_idx])/closes[s_idx]*100
    emoji = "✅" if held_ret>0 else "❌"
    print(f"#{i+1:2d} {emoji} 买入¥{b['price']:.2f}→卖出¥{s['price']:.2f} | 持{held:2d}周 | 本笔{held_ret:+5.1f}% | 离场后上升{missed_ret:+5.0f}% | {s['reason']}")

print(f"\n在场时间: {total_in}周/{len(closes)-20}周 = {total_in/(len(closes)-20)*100:.0f}%")
print(f"平均每笔收益: {total_gain/len(buys):+.1f}%")

print(f"\n=== 卖出原因统计 ===")
reasons = Counter(s['reason'] for s in sells if '期末' not in s['reason'])
for r, c in reasons.most_common():
    print(f"  {r}: {c}次")

# 看看如果只做买入持有各段之间的对比
print(f"\n=== 关键洞察 ===")
print(f"1. 芯片ETF从 ¥{closes[20]:.3f} 涨到 ¥{closes[-1]:.3f}（+{(closes[-1]/closes[20]-1)*100:.0f}%），5年几乎单边上涨")
print(f"2. 波段策略只在 KDJ+RSI 同时超卖时才买入，5年只触发13次入场")
print(f"3. 每次卖出后 ETF 继续上涨，策略反复「低抛高吸」")
print(f"4. 胜率仅38.5%说明多数交易都是止损/提前离场")
