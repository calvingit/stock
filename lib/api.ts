// API client for FastAPI backend (via Next.js API Route proxy)
const API_BASE = '/api/api';

export interface BacktestParams {
  mode?: 'etf' | 'strategy';
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

export interface BacktestResult {
  status: string;
  cumulative_return: number;
  annual_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  calmar_ratio: number;
  equity_curve: [string, number][];
  drawdown_curve: [string, number][];
  trades: TradeRecord[];
  summary: Record<string, unknown>;
}

export interface TradeRecord {
  date: string;
  code: string;
  name: string;
  action: 'buy' | 'sell';
  price: number;
  shares?: number;
  reason?: string;
  pnl?: number;
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
  status: string;
  annual_return: number;
  volatility: number;
  max_drawdown: number;
  sharpe_ratio: number;
  calmar_ratio: number;
  final_value: number;
  rebalance_count: number;
  equity_curve: [string, number][];
  drawdown_curve: [string, number][];
  yearly_returns: Record<string, number>;
  correlation_matrix: Record<string, Record<string, number>>;
}

async function fetchAPI<T>(path: string, params: Record<string, string | number | boolean | undefined> = {}): Promise<T> {
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
};
