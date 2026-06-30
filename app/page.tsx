'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, type StrategyMeta } from '@/lib/api';
import { EquityChart } from '@/components/charts/EquityChart';

export default function Dashboard() {
  const [strategies, setStrategies] = useState<StrategyMeta[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.strategies()
      .then((data) => setStrategies(data.strategies))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">加载中...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2">策略超市</h2>
        <p className="text-muted-foreground">基于历史数据的量化策略回测平台 · Next.js 16 + ECharts 6</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {strategies.map((s) => (
          <Link
            key={s.id}
            href={`/${s.id}`}
            className="block p-5 rounded-lg border border-border hover:border-primary bg-card hover:bg-accent transition-all group"
          >
            <div className="flex items-start justify-between mb-3">
              <span className="text-3xl">{s.icon}</span>
              {s.metrics.sharpe_ratio && (
                <span className="text-xs px-2 py-0.5 rounded bg-primary/10 text-primary font-mono">
                  Sharpe {s.metrics.sharpe_ratio.toFixed(2)}
                </span>
              )}
            </div>
            <h3 className="text-lg font-semibold mb-1 group-hover:text-primary transition-colors">{s.name}</h3>
            <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{s.description}</p>
            <div className="flex gap-3 text-xs">
              {s.metrics.cumulative_return && (
                <span className="text-green-400 font-mono">
                  +{(s.metrics.cumulative_return * 100).toFixed(0)}%
                </span>
              )}
              {s.metrics.max_drawdown && (
                <span className="text-red-400 font-mono">
                  {(s.metrics.max_drawdown * 100).toFixed(0)}%
                </span>
              )}
              {s.metrics.calmar_ratio && (
                <span className="text-yellow-400 font-mono">
                  C {s.metrics.calmar_ratio.toFixed(1)}
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>

      {/* Quick comparison hint */}
      <div className="p-4 rounded-lg border border-border bg-card/50">
        <p className="text-sm text-muted-foreground text-center">
          💡 点击卡片进入策略详情 · 左侧导航切换功能 · 参数可实时预览
        </p>
      </div>
    </div>
  );
}
