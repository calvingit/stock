'use client';

import { useState, useEffect, useCallback } from 'react';
import { EquityChart } from '@/components/charts/EquityChart';
import { DrawdownChart } from '@/components/charts/DrawdownChart';
import { Slider } from '@/components/ui/Slider';
import { fetchAPI } from '@/lib/api';

interface IndustryRotationResult {
  mode: string;
  params: Record<string, unknown>;
  result: {
    nav_series: number[];
    daily_dates: string[];
    trades: Array<{
      type: string;
      code: string;
      date: string;
      price: number;
      shares: number;
      proceeds: number;
      pnl: number;
      pnl_pct: number;
      reason: string;
    }>;
    stats: {
      final_value: number;
      total_return: number;
      max_drawdown: number;
      num_trades: number;
      num_buys: number;
      num_sells: number;
      win_rate: number;
      avg_win: number;
      avg_loss: number;
      total_pnl: number;
      initial_capital: number;
    };
  };
}

function normEquityCurve(navSeries: number[], dates: string[]): [string, number][] {
  if (!navSeries?.length) return [];
  return navSeries.map((v, i) => {
    const d = dates[i] || '';
    const formatted = d.length === 8 ? `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6)}` : d;
    return [formatted, v] as [string, number];
  });
}

function calcDrawdown(navSeries: number[]): [string, number][] {
  if (!navSeries?.length) return [];
  let peak = navSeries[0];
  return navSeries.map((v, i) => {
    if (v > peak) peak = v;
    const dd = (v - peak) / peak;
    return [i.toString(), dd * 100] as [string, number];
  });
}

export default function IndustryRotationPage() {
  const [params, setParams] = useState({
    fast_ma: 5, mid_ma: 15, slow_ma: 50,
    trail_stop: 7, max_positions: 2,
  });
  const [result, setResult] = useState<IndustryRotationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runBacktest = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAPI<IndustryRotationResult>('backtest/industry_rotation', {
        fast_ma: params.fast_ma,
        mid_ma: params.mid_ma,
        slow_ma: params.slow_ma,
        trail_stop: params.trail_stop,
        max_positions: params.max_positions,
      });
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '请求失败');
    } finally {
      setLoading(false);
    }
  }, [params]);

  useEffect(() => { runBacktest(); }, [runBacktest]);

  const navSeries = result?.result?.nav_series;
  const dates = result?.result?.daily_dates;
  const stats = result?.result?.stats;
  const equityCurve = normEquityCurve(navSeries || [], dates || []);
  const drawdownCurve = calcDrawdown(navSeries || []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">🏭 行业轮动</h2>
        <p className="text-muted-foreground mt-1">申万行业 ETF 轮动 + CSI300 择时 + 移动止损 · 持仓 {params.max_positions} 只</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4 p-4 rounded-lg border border-border bg-card">
          <h3 className="font-semibold">参数配置</h3>
          <Slider label="短期 MA" value={params.fast_ma} min={3} max={20} step={1} onChange={(v) => setParams(p => ({ ...p, fast_ma: v }))} />
          <Slider label="长期 MA" value={params.mid_ma} min={10} max={60} step={1} onChange={(v) => setParams(p => ({ ...p, mid_ma: v }))} />
          <Slider label="信号 MA" value={params.slow_ma} min={30} max={200} step={5} onChange={(v) => setParams(p => ({ ...p, slow_ma: v }))} />
          <Slider label="止损 %" value={params.trail_stop} min={3} max={15} step={0.5} onChange={(v) => setParams(p => ({ ...p, trail_stop: v }))} />
          <Slider label="持仓数" value={params.max_positions} min={1} max={5} step={1} onChange={(v) => setParams(p => ({ ...p, max_positions: v }))} />
          <button onClick={runBacktest} disabled={loading}
            className="w-full py-2 px-4 rounded-md bg-primary text-primary-foreground font-medium disabled:opacity-50 hover:opacity-90">
            {loading ? '计算中...' : '运行回测'}
          </button>
        </div>
        <div className="lg:col-span-2 space-y-4">
          {error && <div className="p-3 rounded bg-red-500/10 text-red-400 text-sm">{error}</div>}
          {stats ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatCard label="累计收益" value={`${stats.total_return.toFixed(1)}%`} color={stats.total_return >= 0 ? 'text-green-400' : 'text-red-400'} />
                <StatCard label="最大回撤" value={`${stats.max_drawdown.toFixed(1)}%`} color="text-red-400" />
                <StatCard label="交易次数" value={`${stats.num_trades}`} color="text-cyan-400" />
                <StatCard label="胜率" value={`${stats.win_rate.toFixed(0)}%`} color="text-yellow-400" />
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
