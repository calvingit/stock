'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { Slider } from '@/components/ui/Slider';

export default function BuyTimingPage() {
  const [code, setCode] = useState('159941');
  const [rsiPeriod, setRsiPeriod] = useState(14);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const runAnalysis = async () => {
    setLoading(true);
    try {
      const data = await api.buyTiming({ code, rsi_period: rsiPeriod });
      setResult(data as Record<string, unknown>);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">🎯 右侧买入时机</h2>
        <p className="text-muted-foreground mt-1">趋势确认信号 + RSI 突破 · 不抄底，等趋势起来再追入</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4 p-4 rounded-lg border border-border bg-card">
          <h3 className="font-semibold">参数</h3>
          <div>
            <label className="text-sm text-muted-foreground block mb-1">ETF 代码</label>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full p-2 rounded-md bg-secondary border border-border text-sm font-mono"
              placeholder="如: 159941"
            />
          </div>
          <Slider label="RSI 周期" value={rsiPeriod} min={6} max={30} step={1}
            onChange={(v) => setRsiPeriod(v)} />
          <button onClick={runAnalysis} disabled={loading}
            className="w-full py-2 px-4 rounded-md bg-primary text-primary-foreground font-medium disabled:opacity-50 hover:opacity-90">
            {loading ? '分析中...' : '分析时机'}
          </button>
        </div>

        <div className="lg:col-span-2 space-y-4">
          {result ? (
            <div className="p-4 rounded-lg border border-border bg-card">
              <pre className="text-xs overflow-auto max-h-96 text-muted-foreground">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 rounded-lg border border-border bg-card text-muted-foreground">
              输入 ETF 代码后点击「分析时机」
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
