'use client';

import { useState, useMemo } from 'react';

export interface TradeRow {
  date: string;
  code?: string;
  name?: string;
  action: 'buy' | 'sell';
  price: number;
  shares?: number;
  pnl?: number;
  reason?: string;
}

interface TradeTableProps {
  trades: TradeRow[];
  title?: string;
}

export function TradeTable({ trades, title = '交易记录' }: TradeTableProps) {
  const [sortKey, setSortKey] = useState<keyof TradeRow>('date');
  const [sortAsc, setSortAsc] = useState(false);
  const [filterAction, setFilterAction] = useState<'all' | 'buy' | 'sell'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const filteredTrades = useMemo(() => {
    let result = [...trades];
    if (filterAction !== 'all') result = result.filter((t) => t.action === filterAction);
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter((t) => t.code?.toLowerCase().includes(term) || t.name?.toLowerCase().includes(term));
    }
    result.sort((a, b) => {
      const av = a[sortKey] ?? '';
      const bv = b[sortKey] ?? '';
      const cmp = typeof av === 'number' && typeof bv === 'number' ? av - bv : String(av).localeCompare(String(bv));
      return sortAsc ? cmp : -cmp;
    });
    return result;
  }, [trades, filterAction, searchTerm, sortKey, sortAsc]);

  const exportCSV = () => {
    const headers = ['日期', '代码', '名称', '操作', '价格', '数量', '盈亏', '原因'];
    const rows = filteredTrades.map((t) => [t.date, t.code || '', t.name || '', t.action, t.price, t.shares || '', t.pnl ?? '', t.reason || '']);
    const csv = [headers, ...rows].map((r) => r.join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trades_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSort = (key: keyof TradeRow) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(true); }
  };

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold">{title} ({filteredTrades.length}笔)</h4>
        <button onClick={exportCSV} className="text-xs px-3 py-1 rounded bg-secondary hover:bg-accent transition">
          导出 CSV
        </button>
      </div>
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          placeholder="搜索代码/名称..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="flex-1 px-3 py-1.5 text-sm rounded bg-secondary border border-border"
        />
        <select
          value={filterAction}
          onChange={(e) => setFilterAction(e.target.value as 'all' | 'buy' | 'sell')}
          className="px-3 py-1.5 text-sm rounded bg-secondary border border-border"
        >
          <option value="all">全部</option>
          <option value="buy">买入</option>
          <option value="sell">卖出</option>
        </select>
      </div>
      <div className="overflow-x-auto max-h-80 overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-card">
            <tr className="border-b border-border">
              {(['date', 'code', 'name', 'action', 'price', 'pnl'] as const).map((key) => (
                <th key={key} className="p-2 text-left cursor-pointer hover:text-primary" onClick={() => handleSort(key)}>
                  {{ date: '日期', code: '代码', name: '名称', action: '操作', price: '价格', pnl: '盈亏' }[key]}
                  {sortKey === key && (sortAsc ? ' ↑' : ' ↓')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredTrades.slice(0, 100).map((t, i) => (
              <tr key={i} className="border-b border-border/50 hover:bg-accent/50">
                <td className="p-2 font-mono">{t.date}</td>
                <td className="p-2 font-mono">{t.code}</td>
                <td className="p-2">{t.name}</td>
                <td className="p-2">
                  <span className={`px-1.5 py-0.5 rounded text-xs ${t.action === 'buy' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                    {t.action === 'buy' ? '买入' : '卖出'}
                  </span>
                </td>
                <td className="p-2 font-mono">{t.price.toFixed(2)}</td>
                <td className={`p-2 font-mono ${(t.pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {t.pnl !== undefined ? `${(t.pnl * 100).toFixed(1)}%` : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
