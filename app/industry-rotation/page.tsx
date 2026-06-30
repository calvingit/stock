'use client';

import { useState } from 'react';
import { EquityChart } from '@/components/charts/EquityChart';
import { DrawdownChart } from '@/components/charts/DrawdownChart';
import { api, type BacktestResult } from '@/lib/api';
import { Slider } from '@/components/ui/Slider';

export default function IndustryRotationPage() {
  const [params, setParams] = useState({ short_ma: 5, long_ma: 15, signal_ma: 50, stop_loss: 7, n_stocks: 2, market_filter: 100 });
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);

  const runBacktest = async () => {
    setLoading(true);
    try {
      const data = await api.backtest({ mode: 'etf', ...params });
      setResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">🏭 行业轮动</h2>
        <p className="text-muted-foreground mt-1">申万行业 ETF 轮动 + CSI300 大盘择时 + 移动止损</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4 p-4 rounded-lg border border-border bg-card">
          <h3 className="font-semibold">参数面板</h3>
          <Slider label="短期 MA" value={params.short_ma} min={3} max={20} step={1}
            onChange={(v) => setParams((p) => ({ ...p, short_ma: v }))} />
          <Slider label="长期 MA" value={params.long_ma} min={10} max={60} step={1}
            onChange={(v) => setParams((p) => ({ ...p, long_ma: v }))} />
          <Slider label="信号 MA" value={params.signal_ma} min={30} max={200} step={5}
            onChange={(v) => setParams((p) => ({ ...p, signal_ma: v }))} />
          <Slider label="止损 %" value={params.stop_loss} min={3} max={15} step={0.5}
            onChange={(v) => setParams((p) => ({ ...p, stop_loss: v }))} />
          <Slider label="持仓数" value={params.n_stocks} min={1} max={5} step={1}
            onChange={(v) => setParams((p) => ({ ...p, n_stocks: v }))} />
          <button onClick={runBacktest} disabled={loading}
            className="w-full py-2 px-4 rounded-md bg-primary text-primary-foreground font-medium disabled:opacity-50 hover:opacity-90">
            {loading ? '运行中...' : '运行回测'}
          </button>
        </div>
        <div className="lg:col-span-2 space-y-4">
          {result ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg border border-border bg-card">
                  <div className="text-xs text-muted-foreground">累计收益</div>
                  <div className="text-xl font-bold text-green-400">{(result.cumulative_return * 100).toFixed(1)}%</div>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <div className="text-xs text-muted-foreground">年化收益</div>
                  <div className="text-xl font-bold text-blue-400">{(result.annual_return * 100).toFixed(1)}%</div>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <div className="text-xs text-muted-foreground">最大回撤</div>
                  <div className="text-xl font-bold text-red-400">{(result.max_drawdown * 100).toFixed(1)}%</div>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <div className="text-xs text-muted-foreground">夏普比率</div>
                  <div className="text-xl font-bold text-yellow-400">{result.sharpe_ratio.toFixed(2)}</div>
                </div>
              </div>
              <div className="p-4 rounded-lg border border-border bg-card">
                <EquityChart data={result.equity_curve} title="净值曲线" height={350} marks={result.trades?.filter(t => t.action === 'buy' || t.action === 'sell').slice(0, 50).map(t => ({ date: t.date, price: t.price, type: t.action }))} />
              </div>
              <div className="p-4 rounded-lg border border-border bg-card">
                <DrawdownChart data={result.drawdown_curve} height={150} />
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-64 rounded-lg border border-border bg-card text-muted-foreground">
              配置参数后点击「运行回测」
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
