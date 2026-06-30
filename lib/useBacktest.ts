'use client';

import { useState, useCallback } from 'react';
import { api, type BacktestResult, type BacktestResultItem, normEquityCurve } from './api';

export function useBacktest() {
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (params: Record<string, string | number | boolean | undefined>) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.backtest(params);
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  return { result, loading, error, run };
}

export function getItem(result: BacktestResult | null): BacktestResultItem | null {
  return result?.results?.[0] || null;
}

export function getEquityCurve(item: BacktestResultItem | null): [string, number][] {
  return item ? normEquityCurve(item.equity_curve) : [];
}

export function getDrawdownCurve(item: BacktestResultItem | null): [string, number][] {
  return item ? normEquityCurve(item.drawdown_curve) : [];
}
