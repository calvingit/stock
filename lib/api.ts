// API client for FastAPI backend (via Next.js API Route proxy)
const API_BASE = '/api/api';

export interface BacktestParams {
  mode?: 'etf' | 'strategy';
  codes?: string;
  fast_ma?: number;
  mid_ma?: number;
  slow_ma?: number;
  hard_stop?: number;
  trail_stop?: number;
  initial_capital?: number;
  volume_confirm?: number;
  pause_after_losses?: number;
  strategy_sets?: string;
  begin?: string;
  end?: string;
  short_ma?: number;
  long_ma?: number;
  signal_ma?: number;
  stop_loss?: number;
  n_stocks?: number;
  market_filter?: number;
  start_date?: string;
  end_date?: string;
  commission?: number;
  stamp_tax?: number;
  slippage?: number;
}

export interface BacktestResultItem {
  code: string;
  final_value: number;
  total_return: number; // percentage
  buy_hold_return: number;
  alpha: number;
  trade_count: number;
  win_rate: number;
  avg_gain: number;
  worst_trade: number;
  max_drawdown: number; // percentage (positive number like 24.97)
  sharpe_approx: number;
  skipped_volume: number;
  skipped_pause: number;
  gains: number[];
  nav_series: number[];
  closes: number[];
  min_days: number;
  marks: { idx: number; type: string; price: number }[];
  trade_summary: number;
  equity_curve: [string, number][]; // dates are YYYYMMDD
  drawdown_curve: [string, number][];
  label?: string;
  strategy_params?: Record<string, number>;
  error?: string;
}

export interface BacktestResult {
  mode: string;
  params: Record<string, number | string>;
  period: string;
  results: BacktestResultItem[];
}

// Helper: convert YYYYMMDD to YYYY-MM-DD
export function fmtDate(d: string): string {
  return d.length === 8 ? `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6)}` : d;
}

// Helper: normalize equity curve dates
export function normEquityCurve(data: [string, number][]): [string, number][] {
  return data.map(([d, v]) => [fmtDate(d), v]);
}

export interface TradeRecord {
  date: string;
  code: string;
  name?: string;
  action: 'buy' | 'sell';
  price: number;
  shares?: number;
  reason?: string;
  pnl?: number;
  idx?: number;
}

export interface AssetAllocationParams {
  w1: number; // 纳指
  w2: number; // 红利低波
  w3: number; // 政金债
  w4: number; // 黄金
  rebalance: 'monthly' | 'quarterly' | 'semi-annual' | 'annual' | 'threshold' | 'none';
  start_date?: string;
  end_date?: string;
}

export interface AssetAllocationResult {
  status?: string;
  ann_return: number;  // 年化收益率 (百分比, 如 24.61)
  volatility: number;  // 波动率 (百分比)
  max_drawdown: number;  // 最大回撤 (百分比, 如 -12.62)
  sharpe: number;
  calmar: number;
  total_return: number;  // 总收益百分比
  final_value: number;
  rebalance_count: number;
  nav_series: number[];  // 净值序列
  dates: string[];  // 日期序列 (YYYYMMDD)
  annual_returns: Record<string, number>;  // 年度收益 (百分比)
  correlation: Record<string, Record<string, number>>;
  individual_navs?: Record<string, number[]>;
  weights?: Record<string, number>;
}

// Helper to get equity curve in [date, value] format
export function getEquityCurve(result: AssetAllocationResult): [string, number][] {
  return result.dates.map((d, i) => [d.slice(0, 4) + '-' + d.slice(4, 6) + '-' + d.slice(6), result.nav_series[i]]);
}

// Helper to get drawdown curve
export function getDrawdownCurve(result: AssetAllocationResult): [string, number][] {
  const nav = result.nav_series;
  let peak = nav[0];
  return result.dates.map((d, i) => {
    peak = Math.max(peak, nav[i]);
    const dd = (nav[i] - peak) / peak;
    return [d.slice(0, 4) + '-' + d.slice(4, 6) + '-' + d.slice(6), dd] as [string, number];
  });
}

export async function fetchAPI<T>(path: string, params: Record<string, string | number | boolean | undefined> = {}): Promise<T> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) searchParams.set(key, String(value));
  });
  const query = searchParams.toString();
  const url = `${API_BASE}/${path}${query ? '?' + query : ''}`;
  
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(error.error || `API error: ${res.status}`);
  }
  return res.json();
}

// Strategy metadata
export interface StrategyMeta {
  id: string;
  name: string;
  icon: string;
  description: string;
  best_params: Record<string, number | string>;
  metrics: Record<string, number>;
}

export interface FrontierPoint {
  risk: number;
  return: number;
  sharpe: number;
  weights: [number, number, number, number];
}

export interface PlaneCell {
  nasdaq: number;
  bond_ratio: number;
  bond: number;
  gold: number;
  ann_return: number | null;
  max_drawdown: number | null;
  sharpe: number | null;
  calmar: number | null;
}

export interface PlaneResult {
  status: string;
  x_labels: number[];
  y_labels: number[];
  grid: Record<string, PlaneCell>;
}

export interface GradientResult {
  nasdaq: number;
  bond: number;
  gold: number;
  annual_return: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  calmar_ratio: number | null;
  final_value: number | null;
}

export const api = {
  // Health check
  health: () => fetchAPI<{ status: string }>('health'),

  // Backtest strategies
  backtest: (params: BacktestParams) => fetchAPI<BacktestResult>('backtest', params as Record<string, string | number | boolean | undefined>),
  
  // Band strategy
  bandStrategy: (params: BacktestParams) => fetchAPI<BacktestResult>('backtest/band', params as Record<string, string | number | boolean | undefined>),
  
  // Buy timing
  buyTiming: (params: { code?: string; rsi_period?: number }) => 
    fetchAPI<unknown>('buy_timing', params as Record<string, string | number | boolean | undefined>),

  // Asset allocation
  assetAllocation: (params: AssetAllocationParams) =>
    fetchAPI<AssetAllocationResult>('asset_allocation', {
      w1: params.w1,
      w2: params.w2,
      w3: params.w3,
      w4: params.w4,
      rebalance: params.rebalance,
      start_date: params.start_date,
      end_date: params.end_date,
    }),

  // Strategy metadata
  strategies: () => fetchAPI<{ strategies: StrategyMeta[] }>('strategies'),

  // Asset allocation gradient
  allocationGradient: (params: { rebalance?: string; start_date?: string; end_date?: string }) =>
    fetchAPI<{ results: GradientResult[] }>('asset_allocation/gradient', {
      rebalance: params.rebalance || 'annual',
      begin: params.start_date || '2022-12-14',
      end: params.end_date || '2026-06-30',
    }),

  // Asset allocation parameter plane heatmap
  allocationPlane: (params: { rebalance?: string; start_date?: string; end_date?: string }) =>
    fetchAPI<PlaneResult>('asset_allocation/plane', {
      rebalance: params.rebalance || 'annual',
      begin: params.start_date || '2022-12-14',
      end: params.end_date || '2026-06-30',
    }),

  // Asset allocation efficient frontier
  allocationFrontier: (params: { rebalance?: string; start_date?: string; end_date?: string; samples?: number }) =>
    fetchAPI<{ points: FrontierPoint[] }>('asset_allocation/frontier', {
      rebalance: params.rebalance || 'annual',
      begin: params.start_date || '2022-12-14',
      end: params.end_date || '2026-06-30',
      samples: params.samples || 200,
    }),

  // Backtest detail
  backtestDetail: (params: BacktestParams) => fetchAPI<BacktestResult>('backtest/detail', params as Record<string, string | number | boolean | undefined>),
};

