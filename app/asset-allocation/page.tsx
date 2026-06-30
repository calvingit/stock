'use client';

import { useState } from 'react';
import { EquityChart } from '@/components/charts/EquityChart';
import { DrawdownChart } from '@/components/charts/DrawdownChart';
import { api, type AssetAllocationResult } from '@/lib/api';
import { Slider } from '@/components/ui/Slider';

const REBALANCE_OPTIONS = [
  { value: 'monthly', label: '月度' },
  { value: 'quarterly', label: '季度' },
  { value: 'semi-annual', label: '半年' },
  { value: 'annual', label: '年度' },
  { value: 'threshold', label: '阈值触发' },
  { value: 'none', label: '不调整' },
];

export default function AssetAllocationPage() {
  const [params, setParams] = useState({ w1: 25, w2: 25, w3: 25, w4: 25, rebalance: 'annual' as const });
  const [result, setResult] = useState<AssetAllocationResult | null>(null);
  const [loading, setLoading] = useState(false);

  const runAllocation = async () => {
    setLoading(true);
    try {
      const data = await api.assetAllocation(params);
      setResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const total = params.w1 + params.w2 + params.w3 + params.w4;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">🏛️ 资产配置</h2>
        <p className="text-muted-foreground mt-1">纳指100 + 红利低波 + 政金债 + 黄金 · 固定比例 + 再平衡</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4 p-4 rounded-lg border border-border bg-card">
          <h3 className="font-semibold">配置比例</h3>
          <Slider label="广发纳指100 (159941)" value={params.w1} min={0} max={100} step={5}
            onChange={(v) => setParams((p) => ({ ...p, w1: v }))} />
          <Slider label="红利低波100 (515100)" value={params.w2} min={0} max={100} step={5}
            onChange={(v) => setParams((p) => ({ ...p, w2: v }))} />
          <Slider label="政金债ETF (511580)" value={params.w3} min={0} max={100} step={5}
            onChange={(v) => setParams((p) => ({ ...p, w3: v }))} />
          <Slider label="黄金ETF (518880)" value={params.w4} min={0} max={100} step={5}
            onChange={(v) => setParams((p) => ({ ...p, w4: v }))} />
          
          <div className={`text-sm text-center py-1 rounded ${total === 100 ? 'text-green-400 bg-green-400/10' : 'text-red-400 bg-red-400/10'}`}>
            总计: {total}% {total !== 100 ? '(需=100%)' : '✓'}
          </div>

          <div>
            <label className="text-sm text-muted-foreground block mb-1">再平衡频率</label>
            <select
              value={params.rebalance}
              onChange={(e) => setParams((p) => ({ ...p, rebalance: e.target.value as typeof p.rebalance }))}
              className="w-full p-2 rounded-md bg-secondary border border-border text-sm"
            >
              {REBALANCE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          <button onClick={runAllocation} disabled={loading || total !== 100}
            className="w-full py-2 px-4 rounded-md bg-primary text-primary-foreground font-medium disabled:opacity-50 hover:opacity-90">
            {loading ? '计算中...' : '运行回测'}
          </button>
        </div>

        <div className="lg:col-span-2 space-y-4">
          {result ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg border border-border bg-card">
                  <div className="text-xs text-muted-foreground">年化收益</div>
                  <div className="text-xl font-bold text-green-400">{(result.annual_return * 100).toFixed(1)}%</div>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <div className="text-xs text-muted-foreground">波动率</div>
                  <div className="text-xl font-bold text-blue-400">{(result.volatility * 100).toFixed(1)}%</div>
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
                <EquityChart data={result.equity_curve} title="净值曲线" height={350} />
              </div>
              <div className="p-4 rounded-lg border border-border bg-card">
                <DrawdownChart data={result.drawdown_curve} height={150} />
              </div>
              {result.yearly_returns && (
                <div className="p-4 rounded-lg border border-border bg-card">
                  <h4 className="text-sm font-semibold mb-3">年度收益</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {Object.entries(result.yearly_returns).map(([year, ret]) => (
                      <div key={year} className="p-2 rounded bg-secondary text-center">
                        <div className="text-xs text-muted-foreground">{year}</div>
                        <div className={`text-sm font-bold ${(ret as number) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {((ret as number) * 100).toFixed(1)}%
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center justify-center h-64 rounded-lg border border-border bg-card text-muted-foreground">
              调整配置比例后点击「运行回测」
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
