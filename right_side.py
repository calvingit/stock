"""
右侧趋势策略回测（周线）
方案A: MA金叉死叉（周线版）
方案B: RSI趋势跟踪（RSI上穿50买入，下穿50卖出）
方案C: 价格突破N周高点买入 + 移动止损
方案D: MA多头+RSI>50 + 移损
"""
import json

cache_file = "/tmp/etf_backtest_cache/w_159995.SZ_2021-01-01_2026-06-11.json"
with open(cache_file) as f:
    data = json.load(f)

closes = data['closes']
dates = data['dates']

def ma(arr, idx, n):
    if idx < n-1: return None
    return sum(arr[idx-n+1:idx+1]) / n

def run(name, buy_fn, sell_fn, warmup=30):
    cap, shares, in_pos = 1000000, 0, False
    highest, cost_basis, trades = 0, 0, []
    nav = [cap] * warmup
    
    for i in range(warmup, len(closes)):
        p = closes[i]
        
        if in_pos:
            if p > highest: highest = p
            reason = sell_fn(i, p, highest, cost_basis)
            if reason:
                cap += shares * p * 0.9997
                profit = (p - cost_basis) / cost_basis * 100
                trades.append(("卖", i, p, f"{reason} 盈亏{profit:+.1f}%"))
                shares = 0; in_pos = False
        
        if not in_pos:
            if buy_fn(i, p):
                shares = int(cap / (p * 1.0003))
                cap -= shares * p * 1.0003
                cost_basis = p; highest = p; in_pos = True
                trades.append(("买", i, p, ""))
        
        nav.append(cap + shares * p)
    
    if in_pos:
        cap += shares * closes[-1] * 0.9997
        trades.append(("卖", len(closes)-1, closes[-1], "期末"))
    
    ret = (cap - 1000000) / 10000
    bh = (closes[-1] - closes[warmup]) / closes[warmup] * 100
    
    buys = sum(1 for t in trades if t[0]=='买')
    gains = []
    for j in range(0, len(trades)-1, 2):
        if j+1 < len(trades) and trades[j][0]=='买':
            gains.append((trades[j+1][2]-trades[j][2])/trades[j][2]*100)
    wr = sum(1 for g in gains if g>0)/len(gains)*100 if gains else 0
    
    peak_v = 1000000; max_dd = 0
    for v in nav:
        if v > peak_v: peak_v = v
        dd = (peak_v-v)/peak_v*100
        if dd > max_dd: max_dd = dd
    
    return name, ret, bh, buys, wr, round(max_dd,1), trades, nav


from band_backtest import calc_rsi
rsi_vals = calc_rsi(closes)

results = []

# === A: 周线MA金叉死叉 ===
for f_ma, s_ma in [(5,20), (10,30), (10,20), (4,10)]:
    def make_buy_A(f, s):
        def fn(i, p):
            mf = ma(closes, i, f); ms = ma(closes, i, s)
            if mf and ms and i > 0:
                mf_prev = ma(closes, i-1, f); ms_prev = ma(closes, i-1, s)
                if mf_prev and ms_prev:
                    return mf > ms and mf_prev <= ms_prev
            return False
        return fn
    def make_sell_A(f, s):
        def fn(i, p, h, cb):
            mf = ma(closes, i, f); ms = ma(closes, i, s)
            if mf and ms and i > 0:
                mf_prev = ma(closes, i-1, f); ms_prev = ma(closes, i-1, s)
                if mf_prev and ms_prev:
                    if mf < ms and mf_prev >= ms_prev:
                        return f"死叉{f}/{s}"
            return None
        return fn
    results.append(run(f"MA{f_ma}/{s_ma}金叉死叉", make_buy_A(f_ma,s_ma), make_sell_A(f_ma,s_ma)))

# === B: 周线MA多头持仓+移损 ===
for f_m, s_m in [(5,20), (4,10), (5,10)]:
    for trail in [8, 10, 12, 15]:
        def make_buy_B(f, s):
            def fn(i, p):
                mf = ma(closes, i, f); ms = ma(closes, i, s)
                return mf and ms and mf > ms
            return fn
        def make_sell_B(trail):
            def fn(i, p, h, cb):
                if (h - p) / h * 100 >= trail:
                    return f"移-{trail}%"
                return None
            return fn
        results.append(run(f"MA{f_m}/{s_m}多头+移{trail}%", make_buy_B(f_m,s_m), make_sell_B(trail)))

# === C: RSI趋势跟踪 (上穿50买, 下穿45卖) + 移损 ===
for b_lvl, s_lvl in [(50,45), (55,45), (50,40)]:
    for trail in [8, 10, 12]:
        def make_buy_C(bl):
            def fn(i, p):
                if i > 0 and rsi_vals[i] and rsi_vals[i-1]:
                    return rsi_vals[i] > bl and rsi_vals[i-1] <= bl
                return False
            return fn
        def make_sell_C(sl, trail):
            def fn(i, p, h, cb):
                if rsi_vals[i] and rsi_vals[i] < sl:
                    return f"RSI<{sl}"
                if (h-p)/h*100 >= trail:
                    return f"移-{trail}%"
                return None
            return fn
        results.append(run(f"RSI上穿{b_lvl}买/下穿{s_lvl}卖+移{trail}%", 
                          make_buy_C(b_lvl), make_sell_C(s_lvl, trail)))

# 打印结果
print(f"{'策略':<35} {'收益%':>7} {'持有%':>7} {'交易':>5} {'胜率':>6} {'回撤':>7}")
print("-"*75)

results.sort(key=lambda x: -x[1])  # 按收益降序
for r in results[:25]:
    name, ret, bh, tr, wr, dd = r[:6]
    if tr > 0:
        print(f"{name:<35} {ret:>+6.1f}% {bh:>+6.1f}% {tr:>5} {wr:>5.1f}% {dd:>6.1f}%")

bh_all = (closes[-1]-closes[30])/closes[30]*100
print(f"\n{'买入持有':<35} {bh_all:>+6.1f}%")

# 最佳策略详情
best = results[0]
print(f"\n=== 最佳: {best[0]} ===")
for t in best[6]:
    if t[0] == '买':
        print(f"  买 @ ¥{t[2]:.3f}  (第{t[1]}周)")
    else:
        print(f"  卖 @ ¥{t[2]:.3f}  {t[3]}  (第{t[1]}周)")
