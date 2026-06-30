'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navItems = [
  { href: '/', label: '📊 Dashboard' },
  { href: '/ma-crossover', label: '📈 均线多头' },
  { href: '/multi-strategy', label: '🔄 多策略对比' },
  { href: '/band-strategy', label: '📉 波段策略' },
  { href: '/rsi-trend', label: '📊 RSI 趋势' },
  { href: '/industry-rotation', label: '🏭 行业轮动' },
  { href: '/asset-allocation', label: '🏛️ 资产配置' },
  { href: '/buy-timing', label: '🎯 右侧买入' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 border-r border-border bg-card h-screen sticky top-0 flex flex-col">
      <div className="p-4 border-b border-border">
        <h1 className="text-lg font-bold text-primary">ETF 回测平台</h1>
        <p className="text-xs text-muted-foreground mt-1">量化策略 · 资产配置</p>
      </div>
      <nav className="flex-1 overflow-y-auto p-2">
        {navItems.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block px-3 py-2 rounded-md text-sm mb-1 transition-colors ${
                active
                  ? 'bg-primary text-primary-foreground font-medium'
                  : 'hover:bg-accent hover:text-accent-foreground'
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t border-border text-xs text-muted-foreground">
        v2.0 · Next.js 16
      </div>
    </aside>
  );
}
