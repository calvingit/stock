'use client';

import { useState } from 'react';
import { EquityChart } from '@/components/charts/EquityChart';
import { api, type BacktestResult } from '@/lib/api';

export default function MultiStrategyPage() {
  const [results, setResults] = useState<Record<string, BacktestResult>>({});
  const [loading, setLoading] = useState(false);

  const runAll = async () => {
    setLoading(true);
    const configs: Record<string, Record<string, number>> = {
      'MA5/15/50': { short_ma: 5, long_ma: 15, signal_ma: 50, stop_loss: 7, n_stocks: 2 },
      'MA5/20/100': { short_ma: 5, long_ma: 20, signal_ma: 100, stop_loss: 7, n_stocks: 2 },
      'MA10/30/100': { short_ma: 10, long_ma: 30, signal_ma: 100, stop_loss: 8, n_stocks: 3 },
      'MA5/10/60': { short_ma: 5, long_ma: 10, signal_ma: 60, stop_loss: 5, n_stocks: 2 },
    };
    const out: Record<string, BacktestResult> = {};
    for (const [name, params] of Object.entries(configs)) {
      try {
        out[name] = await api.backtest({ mode: 'strategy', ...params, market_filter: 100 });
      } catch (e) {
        console.error(`Failed: ${name}`, e);
      }
    }
    setResults(out);
    setLoading(false);
  };

  const colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'];
  const overlay = Object.entries(results).map(([name, r], i) => ({
    name,
    data: r.equity_curve,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">🔄 多策略对比</h2>
        <p className="text-muted-foreground mt-1">并排比较多个参数配置的回测表现</p>
      </div>

      <button onClick={runAll} disabled={loading}
        className="py-2 px-6 rounded-md bg-primary text-primary-foreground font-medium disabled:opacity-50">
        {loading ? '运行中...' : '运行全部对比'}
      </button>

      {Object.keys(results).length > 0 && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(results).map(([name, r]) => (
              <div key={name} className="p-3 rounded-lg border border-border bg-card">
                <div className="text-xs text-muted-foreground font-medium">{name}</div>
                <div className="text-lg font-bold text-green-400">{(r.cumulative_return * 100).toFixed(1)}%</div>
                <div className="text-xs text-muted-foreground">夏普: {r.sharpe_ratio.toFixed(2)} | DD: {(r.max_drawdown * 100).toFixed(1)}%</div>
              </div>
            ))}
          </div>
          <div className="p-4 rounded-lg border border-border bg-card">
            <EquityChart data={Object.values(results)[0]?.equity_curve || []} title="净值对比" height={400} overlay={overlay.slice(1)} />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="p-2 text-left">策略</th>
                  <th className="p-2 text-right">累计收益</th>
                  <th className="p-2 text-right">年化</th>
                  <th className="p-2 text-right">最大回撤</th>
                  <th className="p-2 text-right">夏普</th>
                  <th className="p-2 text-right">Calmar</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(results).map(([name, r]) => (
                  <tr key={name} className="border-b border-border">
                    <td className="p-2 font-medium">{name}</td>
                    <td className="p-2 text-right text-green-400">{(r.cumulative_return * 100).toFixed(1)}%</td>
                    <td className="p-2 text-right">{(r.annual_return * 100).toFixed(1)}%</td>
                    <td className="p-2 text-right text-red-400">{(r.max_drawdown * 100).toFixed(1)}%</td>
                    <td className="p-2 text-right">{r.sharpe_ratio.toFixed(2)}</td>
                    <td className="p-2 text-right">{r.calmar_ratio?.toFixed(2) || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
