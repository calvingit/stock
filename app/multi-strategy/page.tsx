'use client';

import { useState } from 'react';
import { EquityChart } from '@/components/charts/EquityChart';
import { api, type BacktestResult, type BacktestResultItem, normEquityCurve } from '@/lib/api';

const STRATEGY_SETS = [
  { name: '激进(5/10/20)', fast_ma: 5, mid_ma: 10, slow_ma: 20, trail_stop: 0.05 },
  { name: '标准(5/15/50)', fast_ma: 5, mid_ma: 15, slow_ma: 50, trail_stop: 0.07 },
  { name: '保守(10/20/60)', fast_ma: 10, mid_ma: 20, slow_ma: 60, trail_stop: 0.10 },
];

export default function MultiStrategyPage() {
  const [results, setResults] = useState<Record<string, BacktestResult | null>>({});
  const [loading, setLoading] = useState(false);

  const runAll = async () => {
    setLoading(true);
    const out: Record<string, BacktestResult | null> = {};
    for (const s of STRATEGY_SETS) {
      try {
        out[s.name] = await api.backtest({
          codes: '512880', fast_ma: s.fast_ma, mid_ma: s.mid_ma, slow_ma: s.slow_ma,
          trail_stop: s.trail_stop, hard_stop: 0, begin: '2022-07-01', end: '2026-06-30',
          mode: 'etf', initial_capital: 1000000, volume_confirm: 0, pause_after_losses: 0,
        });
      } catch { out[s.name] = null; }
    }
    setResults(out);
    setLoading(false);
  };

  const overlay = Object.entries(results).filter(([, r]) => r?.results[0]).map(([name, r]) => ({
    name,
    data: normEquityCurve((r as BacktestResult).results[0].equity_curve),
  }));

  const firstItem = Object.values(results).find((r) => r?.results[0])?.results[0];
  const firstEquityCurve = firstItem ? normEquityCurve(firstItem.equity_curve) : [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">🔀 多策略对比</h2>
        <p className="text-muted-foreground mt-1">单 ETF 多组参数并行回测 · 叠加曲线</p>
      </div>
      <div className="flex gap-3">
        <button onClick={runAll} disabled={loading}
          className="py-2 px-6 rounded-md bg-primary text-primary-foreground font-medium disabled:opacity-50 hover:opacity-90">
          {loading ? '运行中...' : '运行对比'}
        </button>
      </div>
      {Object.keys(results).length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border border-border bg-card">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-border">
                <th className="p-3 text-left">策略</th>
                <th className="p-3 text-right">累计收益</th>
                <th className="p-3 text-right">回撤</th>
                <th className="p-3 text-right">夏普</th>
                <th className="p-3 text-right">交易次数</th>
              </tr></thead>
              <tbody>
                {Object.entries(results).map(([name, r]) => {
                  if (!r?.results[0]) return <tr key={name}><td className="p-3">{name}</td><td colSpan={4} className="p-3 text-muted-foreground">失败</td></tr>;
                  const it = r.results[0];
                  return (
                    <tr key={name} className="border-b border-border hover:bg-accent/50">
                      <td className="p-3 font-medium">{name}</td>
                      <td className="p-3 text-right font-mono text-green-400">{it.total_return.toFixed(1)}%</td>
                      <td className="p-3 text-right font-mono text-red-400">{it.max_drawdown.toFixed(1)}%</td>
                      <td className="p-3 text-right font-mono text-yellow-400">{it.sharpe_approx.toFixed(2)}</td>
                      <td className="p-3 text-right font-mono">{it.trade_count}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="p-4 rounded-lg border border-border bg-card">
            <EquityChart data={firstEquityCurve} title="策略对比" height={400} overlay={overlay} />
          </div>
        </>
      )}
    </div>
  );
}
