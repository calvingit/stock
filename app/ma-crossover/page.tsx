'use client';

import { useState, useEffect } from 'react';
import { EquityChart } from '@/components/charts/EquityChart';
import { DrawdownChart } from '@/components/charts/DrawdownChart';
import { useBacktest, getItem, getEquityCurve, getDrawdownCurve } from '@/lib/useBacktest';
import { Slider } from '@/components/ui/Slider';
import { fmtDate } from '@/lib/api';

const DEFAULTS = { short_ma: 5, long_ma: 15, signal_ma: 50, stop_loss: 7, n_stocks: 2 };

export default function MACrossoverPage() {
  const [params, setParams] = useState(DEFAULTS);
  const { result, loading, error, run } = useBacktest();
  const item = getItem(result);
  const equityCurve = getEquityCurve(item);
  const drawdownCurve = getDrawdownCurve(item);

  useEffect(() => {
    run({ codes: '512880', fast_ma: params.short_ma, mid_ma: params.long_ma, slow_ma: params.signal_ma, trail_stop: params.stop_loss / 100, hard_stop: 0, begin: '2022-07-01', end: '2026-06-30', mode: 'etf', initial_capital: 1000000, volume_confirm: 0, pause_after_losses: 0 });
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">📈 均线多头策略</h2>
        <p className="text-muted-foreground mt-1">MA 金叉入场 + 移动止损 + 大盘择时</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4 p-4 rounded-lg border border-border bg-card">
          <h3 className="font-semibold">参数配置</h3>
          <Slider label="短期 MA" value={params.short_ma} min={3} max={20} step={1} onChange={(v) => setParams(p => ({ ...p, short_ma: v }))} />
          <Slider label="长期 MA" value={params.long_ma} min={10} max={60} step={1} onChange={(v) => setParams(p => ({ ...p, long_ma: v }))} />
          <Slider label="信号 MA" value={params.signal_ma} min={30} max={200} step={5} onChange={(v) => setParams(p => ({ ...p, signal_ma: v }))} />
          <Slider label="止损 %" value={params.stop_loss} min={3} max={15} step={0.5} onChange={(v) => setParams(p => ({ ...p, stop_loss: v }))} />
          <button onClick={() => run({ codes: '512880', fast_ma: params.short_ma, mid_ma: params.long_ma, slow_ma: params.signal_ma, trail_stop: params.stop_loss / 100, hard_stop: 0, begin: '2022-07-01', end: '2026-06-30', mode: 'etf', initial_capital: 1000000, volume_confirm: 0, pause_after_losses: 0 })} disabled={loading}
            className="w-full py-2 px-4 rounded-md bg-primary text-primary-foreground font-medium disabled:opacity-50 hover:opacity-90 transition">
            {loading ? '计算中...' : '运行回测'}
          </button>
        </div>
        <div className="lg:col-span-2 space-y-4">
          {error && <div className="p-3 rounded bg-red-500/10 text-red-400 text-sm">{error}</div>}
          {item ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatCard label="累计收益" value={`${item.total_return.toFixed(1)}%`} color="text-green-400" />
                <StatCard label="最大回撤" value={`${item.max_drawdown.toFixed(1)}%`} color="text-red-400" />
                <StatCard label="夏普" value={item.sharpe_approx.toFixed(2)} color="text-yellow-400" />
                <StatCard label="交易次数" value={`${item.trade_count}`} color="text-cyan-400" />
              </div>
              <div className="p-4 rounded-lg border border-border bg-card">
                <EquityChart data={equityCurve} title="净值曲线" height={350} />
              </div>
              <div className="p-4 rounded-lg border border-border bg-card">
                <DrawdownChart data={drawdownCurve} height={150} />
              </div>
            </>
          ) : (
            !loading && <div className="flex items-center justify-center h-64 rounded-lg border border-border bg-card text-muted-foreground">调整参数后运行回测</div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="p-3 rounded-lg border border-border bg-card">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={`text-lg font-bold mt-1 ${color}`}>{value}</div>
    </div>
  );
}
