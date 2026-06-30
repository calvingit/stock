'use client';

import { useState } from 'react';
import { EquityChart } from '@/components/charts/EquityChart';
import { DrawdownChart } from '@/components/charts/DrawdownChart';
import { api, type BacktestResult, type BacktestResultItem, normEquityCurve } from '@/lib/api';

const STRATEGY_PRESETS = [
  { name: '行业轮动(5/15/50+7%移损)', codes: '512880,513100,515230,512480,512690', fast_ma: 5, mid_ma: 15, slow_ma: 50, trail_stop: 0.07 },
  { name: '保守型(10/20/60+10%移损)', codes: '512880,513100,515230', fast_ma: 10, mid_ma: 20, slow_ma: 60, trail_stop: 0.10 },
  { name: '激进型(5/10/20+5%移损)', codes: '512480,512690,515790,512200', fast_ma: 5, mid_ma: 10, slow_ma: 20, trail_stop: 0.05 },
];

export default function StrategySupermarketPage() {
  const [results, setResults] = useState<Record<string, BacktestResult | null>>({});
  const [loading, setLoading] = useState(false);

  const runComparison = async () => {
    setLoading(true);
    const out: Record<string, BacktestResult | null> = {};
    for (const preset of STRATEGY_PRESETS) {
      try {
        const result = await api.backtest({
          codes: preset.codes,
          fast_ma: preset.fast_ma,
          mid_ma: preset.mid_ma,
          slow_ma: preset.slow_ma,
          trail_stop: preset.trail_stop,
          hard_stop: 0,
          begin: '2023-01-01',
          end: '2026-06-30',
          mode: 'etf',
          initial_capital: 1000000,
          volume_confirm: 0,
          pause_after_losses: 0,
        });
        out[preset.name] = result;
      } catch (e) {
        console.error(e);
        out[preset.name] = null;
      }
    }
    setResults(out);
    setLoading(false);
  };

  // Build overlay from first result item of each strategy
  const overlay = Object.entries(results).filter(([, r]) => r && r.results[0]).map(([name, r]) => ({
    name,
    data: normEquityCurve((r as BacktestResult).results[0].equity_curve),
  }));

  const firstResult = Object.values(results).find((r) => r && r.results[0]);
  const firstEquityCurve = firstResult ? normEquityCurve(firstResult.results[0].equity_curve) : [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">🛒 策略超市</h2>
        <p className="text-muted-foreground mt-1">多策略横向对比 · 叠加曲线 · 风险收益一览</p>
      </div>

      <div className="flex gap-3 items-center">
        <button onClick={runComparison} disabled={loading}
          className="py-2 px-6 rounded-md bg-primary text-primary-foreground font-medium disabled:opacity-50 hover:opacity-90 transition">
          {loading ? '运行中...' : '🔄 运行对比'}
        </button>
        <span className="text-xs text-muted-foreground">
          回测区间: 2023-01-01 ~ 2026-06-30 · 初始资金 100万
        </span>
      </div>

      {Object.keys(results).length > 0 && (
        <>
          {/* Summary comparison table */}
          <div className="overflow-x-auto rounded-lg border border-border bg-card">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="p-3 text-left">策略</th>
                  <th className="p-3 text-left">ETF组合</th>
                  <th className="p-3 text-right">累计收益</th>
                  <th className="p-3 text-right">最大回撤</th>
                  <th className="p-3 text-right">夏普</th>
                  <th className="p-3 text-right">交易次数</th>
                  <th className="p-3 text-right">胜率</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(results).map(([name, r]) => {
                  const item = r?.results?.[0];
                  if (!item) return <tr key={name}><td className="p-3">{name}</td><td colSpan={6} className="p-3 text-muted-foreground">数据获取失败</td></tr>;
                  return (
                    <tr key={name} className="border-b border-border dark:hover:bg-accent/50 hover:bg-accent/50">
                      <td className="p-3 font-medium">{name}</td>
                      <td className="p-3 font-mono text-xs text-muted-foreground">{item.code}</td>
                      <td className="p-3 text-right font-mono text-green-400">{item.total_return.toFixed(1)}%</td>
                      <td className="p-3 text-right font-mono text-red-400">{item.max_drawdown.toFixed(1)}%</td>
                      <td className="p-3 text-right font-mono text-yellow-400">{item.sharpe_approx.toFixed(2)}</td>
                      <td className="p-3 text-right font-mono">{item.trade_count}</td>
                      <td className="p-3 text-right font-mono">{item.win_rate.toFixed(0)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Equity overlay */}
          {overlay.length > 0 && (
            <div className="p-4 rounded-lg border border-border bg-card">
              <EquityChart data={firstEquityCurve} title="策略净值对比" height={400} overlay={overlay} />
            </div>
          )}

          {/* Individual cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(results).map(([name, r]) => {
              const item = r?.results?.[0];
              if (!item) return null;
              return (
                <div key={name} className="p-4 rounded-lg border border-border bg-card space-y-3">
                  <h4 className="font-semibold text-sm">{name}</h4>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="p-2 rounded bg-secondary">
                      <div className="text-muted-foreground">累计收益</div>
                      <div className="font-bold text-green-400">{item.total_return.toFixed(1)}%</div>
                    </div>
                    <div className="p-2 rounded bg-secondary">
                      <div className="text-muted-foreground">最大回撤</div>
                      <div className="font-bold text-red-400">{item.max_drawdown.toFixed(1)}%</div>
                    </div>
                    <div className="p-2 rounded bg-secondary">
                      <div className="text-muted-foreground">买入持有</div>
                      <div className="font-bold">{item.buy_hold_return.toFixed(1)}%</div>
                    </div>
                    <div className="p-2 rounded bg-secondary">
                      <div className="text-muted-foreground">Alpha</div>
                      <div className={`font-bold ${item.alpha >= 0 ? 'text-green-400' : 'text-red-400'}`}>{item.alpha.toFixed(1)}%</div>
                    </div>
                  </div>
                  <div className="p-2 rounded bg-secondary text-xs">
                    <DrawdownChart data={normEquityCurve(item.drawdown_curve).map(([d, v]) => [d, v as number])} height={80} />
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
