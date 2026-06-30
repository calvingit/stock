'use client';

import { useState, useEffect, useMemo } from 'react';
import { EquityChart } from '@/components/charts/EquityChart';
import { DrawdownChart } from '@/components/charts/DrawdownChart';
import { HeatmapChart } from '@/components/charts/HeatmapChart';
import { ScatterChart } from '@/components/charts/ScatterChart';
import { api, getEquityCurve, getDrawdownCurve, type AssetAllocationResult, type GradientResult, type PlaneResult, type FrontierPoint } from '@/lib/api';
import { Slider } from '@/components/ui/Slider';

const REBALANCE_OPTIONS = [
  { value: 'monthly', label: '月度' },
  { value: 'quarterly', label: '季度' },
  { value: 'semi-annual', label: '半年' },
  { value: 'annual', label: '年度' },
  { value: 'threshold', label: '阈值触发' },
  { value: 'none', label: '不调整' },
];

const REBALANCE_CN: Record<string, string> = {
  monthly: '月度再平衡', quarterly: '季度再平衡', 'semi-annual': '半年再平衡',
  annual: '年度再平衡', threshold: '阈值触发', none: '不调整',
};

export default function AssetAllocationPage() {
  const [params, setParams] = useState({ nasdaq: 50, rebalance: 'annual' });
  const [result, setResult] = useState<AssetAllocationResult | null>(null);
  const [gradient, setGradient] = useState<GradientResult[]>([]);
  const [plane, setPlane] = useState<PlaneResult | null>(null);
  const [frontier, setFrontier] = useState<FrontierPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<'config' | 'plane' | 'frontier'>('config');

  const remaining = 100 - params.nasdaq;
  const bond = Math.floor(remaining / 2);
  const gold = remaining - bond;

  const runAllocation = async () => {
    if (params.nasdaq === 100) return;
    setLoading(true);
    try {
      const data = await api.assetAllocation({
        w1: params.nasdaq, w2: 0, w3: bond, w4: gold,
        rebalance: params.rebalance as 'monthly' | 'quarterly' | 'semi-annual' | 'annual' | 'threshold' | 'none',
      });
      setResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadAnalysis = async () => {
    try {
      const [g, p, f] = await Promise.all([
        api.allocationGradient({ rebalance: params.rebalance }),
        api.allocationPlane({ rebalance: params.rebalance }),
        api.allocationFrontier({ rebalance: params.rebalance, samples: 200 }),
      ]);
      setGradient(g.results);
      setPlane(p);
      setFrontier(f.points);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => { loadAnalysis(); }, [params.rebalance]);

  const equityCurve = result ? getEquityCurve(result) : [];
  const drawdownCurve = result ? getDrawdownCurve(result) : [];

  // Prepare plane heatmap data
  const planeData = useMemo(() => {
    if (!plane) return [];
    const data: [number, number, number][] = [];
    for (const key in plane.grid) {
      const cell = plane.grid[key];
      const xIdx = plane.x_labels.indexOf(cell.nasdaq);
      const yIdx = plane.y_labels.indexOf(cell.bond_ratio);
      if (xIdx >= 0 && yIdx >= 0 && cell.sharpe != null) {
        data.push([xIdx, yIdx, cell.sharpe]);
      }
    }
    return data;
  }, [plane]);

  // Prepare frontier scatter data
  const frontierData = useMemo(() => {
    return frontier.map((p) => ({
      x: p.risk,
      y: p.return,
      name: `权重 ${p.weights.join('/')}`,
      itemStyle: { color: p.sharpe > 1.5 ? '#22c55e' : p.sharpe > 1 ? '#fbbf24' : '#60a5fa' },
    }));
  }, [frontier]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">🏛️ 资产配置</h2>
        <p className="text-muted-foreground mt-1">纳指100 + 政金债 + 黄金 · 固定比例 + 再平衡 + 分红再投资</p>
      </div>

      {/* Tab navigation */}
      <div className="flex gap-1 p-1 rounded-lg bg-secondary w-fit">
        {(['config', 'plane', 'frontier'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-1.5 text-sm rounded-md transition ${tab === t ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'}`}>
            {{ config: '⚙️ 配置回测', plane: '🗺️ 参数平面', frontier: '📈 有效前沿' }[t]}
          </button>
        ))}
      </div>

      {tab === 'config' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-4 p-4 rounded-lg border border-border bg-card">
            <h3 className="font-semibold">参数配置</h3>
            <Slider label="纳指 100 (159941) %" value={params.nasdaq} min={10} max={90} step={5}
              onChange={(v) => setParams((p) => ({ ...p, nasdaq: v }))} />
            <div className="p-3 rounded bg-secondary text-sm space-y-1">
              <div className="flex justify-between"><span className="text-muted-foreground">政金债 (511580)</span><span className="font-mono">{bond}%</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">黄金 (518880)</span><span className="font-mono">{gold}%</span></div>
              <div className="text-xs text-muted-foreground mt-1">债:金 = 1:1 自动分配</div>
            </div>
            <div>
              <label className="text-sm text-muted-foreground block mb-1">再平衡频率</label>
              <select value={params.rebalance} onChange={(e) => setParams((p) => ({ ...p, rebalance: e.target.value }))}
                className="w-full p-2 rounded-md bg-secondary border border-border text-sm">
                {REBALANCE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <button onClick={runAllocation} disabled={loading || params.nasdaq === 100}
              className="w-full py-2 px-4 rounded-md bg-primary text-primary-foreground font-medium disabled:opacity-50 hover:opacity-90">
              {loading ? '计算中...' : '运行回测'}
            </button>
          </div>

          <div className="lg:col-span-2 space-y-4">
            {result ? (
              <>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <StatCard label="年化收益" value={`${result.ann_return.toFixed(1)}%`} color="text-green-400" />
                  <StatCard label="波动率" value={`${result.volatility.toFixed(1)}%`} color="text-blue-400" />
                  <StatCard label="最大回撤" value={`${result.max_drawdown.toFixed(1)}%`} color="text-red-400" />
                  <StatCard label="夏普比率" value={result.sharpe.toFixed(2)} color="text-yellow-400" />
                  {result.calmar != null && <StatCard label="Calmar" value={result.calmar.toFixed(2)} color="text-purple-400" />}
                </div>
                <div className="p-4 rounded-lg border border-border bg-card">
                  <EquityChart data={equityCurve} title="组合净值曲线" height={350} />
                </div>
                <div className="p-4 rounded-lg border border-border bg-card">
                  <DrawdownChart data={drawdownCurve} height={150} />
                </div>
                {result.annual_returns && (
                  <div className="p-4 rounded-lg border border-border bg-card">
                    <h4 className="text-sm font-semibold mb-3">年度收益</h4>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                      {Object.entries(result.annual_returns).map(([year, ret]) => (
                        <div key={year} className="p-2 rounded bg-secondary text-center">
                          <div className="text-xs text-muted-foreground">{year}</div>
                          <div className={`text-sm font-bold ${(ret as number) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {(ret as number).toFixed(1)}%
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center justify-center h-64 rounded-lg border border-border bg-card text-muted-foreground">
                调整参数后点击「运行回测」
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'plane' && (
        <div className="space-y-4">
          <div className="p-4 rounded-lg border border-border bg-card">
            <h4 className="text-sm font-semibold mb-1">参数平面热力图 (Sharpe)</h4>
            <p className="text-xs text-muted-foreground mb-3">
              X轴: 纳指配比(10%~90%) · Y轴: 剩余中债券占比(0%~100%) · 颜色: Sharpe比率
            </p>
            {plane ? (
              <HeatmapChart
                data={planeData}
                xLabels={plane.x_labels.map((x) => `${x}%`)}
                yLabels={plane.y_labels.map((y) => `${y}%`)}
                title=""
                height={350}
              />
            ) : <div className="text-sm text-muted-foreground">计算中...</div>}
          </div>

          {/* Gradient table */}
          <div className="p-4 rounded-lg border border-border bg-card">
            <h4 className="text-sm font-semibold mb-1">📊 梯度对比</h4>
            <p className="text-xs text-muted-foreground mb-3">
              债:金 = 1:1 约束 · 纳指 10%~90% · {REBALANCE_CN[params.rebalance] || params.rebalance}
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead><tr className="border-b border-border">
                  {['纳指%','债%','金%','年化%','回撤%','Sharpe','Calmar','终值'].map((h) => (
                    <th key={h} className="p-2 text-left">{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {gradient.filter((g) => g.annual_return != null).map((g) => (
                    <tr key={g.nasdaq} className={`border-b border-border/50 ${g.nasdaq === params.nasdaq ? 'bg-primary/10' : 'hover:bg-accent/50'}`}>
                      <td className="p-2 font-mono font-bold">{g.nasdaq}%</td>
                      <td className="p-2 font-mono">{g.bond}%</td>
                      <td className="p-2 font-mono">{g.gold}%</td>
                      <td className="p-2 text-right font-mono text-green-400">{(g.annual_return ?? 0).toFixed(1)}</td>
                      <td className="p-2 text-right font-mono text-red-400">{(g.max_drawdown ?? 0).toFixed(1)}</td>
                      <td className="p-2 text-right font-mono text-yellow-400">{(g.sharpe_ratio ?? 0).toFixed(2)}</td>
                      <td className="p-2 text-right font-mono">{(g.calmar_ratio ?? 0).toFixed(2)}</td>
                      <td className="p-2 text-right font-mono text-muted-foreground">{g.final_value ? `${(g.final_value / 10000).toFixed(0)}万` : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Correlation */}
          {result?.correlation && (
            <div className="p-4 rounded-lg border border-border bg-card">
              <h4 className="text-sm font-semibold mb-3">相关性矩阵</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {Object.entries(result.correlation).map(([k1, row]) =>
                  Object.entries(row).map(([k2, val]) => (
                    <div key={`${k1}-${k2}`} className="p-2 rounded text-center" style={{
                      backgroundColor: val > 0 ? `rgba(34,197,94,${val * 0.4})` : `rgba(239,68,68,${Math.abs(val) * 0.4})`,
                    }}>
                      <div className="text-[10px] text-muted-foreground">{k1.slice(0, 6)} × {k2.slice(0, 6)}</div>
                      <div className="text-sm font-bold font-mono">{val.toFixed(2)}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'frontier' && (
        <div className="space-y-4">
          <div className="p-4 rounded-lg border border-border bg-card">
            <h4 className="text-sm font-semibold mb-1">有效前沿</h4>
            <p className="text-xs text-muted-foreground mb-3">
              200组随机权重 · X轴=波动率 · Y轴=年化收益 · 颜色=Sharpe(绿{'>'}1.5, 黄{'>'}1)
            </p>
            <ScatterChart data={frontierData} xLabel="波动率 %" yLabel="年化 %" title="" height={400} />
          </div>

          {/* Top Sharpe table */}
          <div className="p-4 rounded-lg border border-border bg-card">
            <h4 className="text-sm font-semibold mb-3">Top 10 Sharpe 组合</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead><tr className="border-b border-border">
                  <th className="p-2 text-left">排名</th>
                  <th className="p-2 text-right">Sharpe</th>
                  <th className="p-2 text-right">年化%</th>
                  <th className="p-2 text-right">波动%</th>
                  <th className="p-2 text-right">纳指%</th>
                  <th className="p-2 text-right">红利%</th>
                  <th className="p-2 text-right">债%</th>
                  <th className="p-2 text-right">金%</th>
                </tr></thead>
                <tbody>
                  {frontier.sort((a, b) => b.sharpe - a.sharpe).slice(0, 10).map((p, i) => (
                    <tr key={i} className="border-b border-border/50 hover:bg-accent/50">
                      <td className="p-2 font-mono">{i + 1}</td>
                      <td className="p-2 text-right font-mono text-yellow-400">{p.sharpe.toFixed(2)}</td>
                      <td className="p-2 text-right font-mono text-green-400">{p.return.toFixed(1)}</td>
                      <td className="p-2 text-right font-mono">{p.risk.toFixed(1)}</td>
                      <td className="p-2 text-right font-mono">{p.weights[0].toFixed(0)}</td>
                      <td className="p-2 text-right font-mono">{p.weights[1].toFixed(0)}</td>
                      <td className="p-2 text-right font-mono">{p.weights[2].toFixed(0)}</td>
                      <td className="p-2 text-right font-mono">{p.weights[3].toFixed(0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  return <div className="p-3 rounded-lg border border-border bg-card"><div className="text-xs text-muted-foreground">{label}</div><div className={`text-lg font-bold mt-1 ${color}`}>{value}</div></div>;
}
