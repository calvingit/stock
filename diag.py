"""诊断脚本 - 看KDJ/RSI/RPS20分布"""
import json, subprocess, os
from band_backtest import fetch_weekly, calc_kdj, calc_rsi, calc_rps20

data = fetch_weekly("159995.SZ", "2021-01-01", "2026-06-11")
closes = data["closes"]
highs = data["highs"]
lows = data["lows"]

K, D, J = calc_kdj(highs, lows, closes)
rsi = calc_rsi(closes)
rps = calc_rps20(closes)

# 有效数据（跳过None）
valid = [(i, K[i], rsi[i], rps[i], closes[i]) for i in range(len(closes)) 
         if K[i] is not None and rsi[i] is not None and rps[i] is not None]

print(f"有效周数: {len(valid)}")
print()

# KDJ_K 分布
k_vals = [v[1] for v in valid]
print(f"KDJ_K:  min={min(k_vals):.0f}  max={max(k_vals):.0f}  median={sorted(k_vals)[len(k_vals)//2]:.0f}")
print(f"  <20: {sum(1 for k in k_vals if k<20)}次  <30: {sum(1 for k in k_vals if k<30)}次  <40: {sum(1 for k in k_vals if k<40)}次")
print(f"  >80: {sum(1 for k in k_vals if k>80)}次  >90: {sum(1 for k in k_vals if k>90)}次")
print()

# RSI 分布
r_vals = [v[2] for v in valid]
print(f"RSI:    min={min(r_vals):.0f}  max={max(r_vals):.0f}  median={sorted(r_vals)[len(r_vals)//2]:.0f}")
print(f"  <20: {sum(1 for r in r_vals if r<20)}次  <30: {sum(1 for r in r_vals if r<30)}次  <40: {sum(1 for r in r_vals if r<40)}次")
print(f"  >80: {sum(1 for r in r_vals if r>80)}次  >90: {sum(1 for r in r_vals if r>90)}次")
print()

# RPS20 分布
p_vals = [v[3] for v in valid]
print(f"RPS20:  min={min(p_vals):.0f}  max={max(p_vals):.0f}  median={sorted(p_vals)[len(p_vals)//2]:.0f}")
print(f"  <10: {sum(1 for p in p_vals if p<10)}次  <20: {sum(1 for p in p_vals if p<20)}次  <30: {sum(1 for p in p_vals if p<30)}次")
print()

# 同时满足 K<40 AND RSI<40 的次数 (宽松版买入条件)
count = sum(1 for v in valid if v[1] < 40 and v[2] < 40 and v[3] >= 10)
print(f"K<40 & RSI<40 & RPS>=10: {count}次")
count = sum(1 for v in valid if v[1] < 35 and v[2] < 35 and v[3] >= 10)
print(f"K<35 & RSI<35 & RPS>=10: {count}次")
count = sum(1 for v in valid if v[1] < 30 and v[2] < 40 and v[3] >= 10)
print(f"K<30 & RSI<40 & RPS>=10: {count}次")
count = sum(1 for v in valid if v[1] < 40 and v[2] < 30 and v[3] >= 10)
print(f"K<40 & RSI<30 & RPS>=10: {count}次")
count = sum(1 for v in valid if v[1] < 30 and v[2] < 30)
print(f"K<30 & RSI<30 (不限RPS): {count}次")
print()

# 最近几周的指标
print("最近10周:")
for v in valid[-10:]:
    print(f"  W{v[0]:3d}  P={v[4]:.3f}  K={v[1]:5.1f}  RSI={v[2]:5.1f}  RPS={v[3]:5.1f}")
