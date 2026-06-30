'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

const navItems = [
  { href: '/', label: '📊 Dashboard' },
  { href: '/ma-crossover', label: '📈 均线多头' },
  { href: '/multi-strategy', label: '🔄 多策略对比' },
  { href: '/band-strategy', label: '📉 波段策略' },
  { href: '/rsi-trend', label: '📊 RSI 趋势' },
  { href: '/industry-rotation', label: '🏭 行业轮动' },
  { href: '/asset-allocation', label: '🏛️ 资产配置' },
  { href: '/buy-timing', label: '🎯 右侧买入' },
  { href: '/strategy-supermarket', label: '🛒 策略超市' },
];

export function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 py-3 border-b border-border bg-card">
        <button onClick={() => setMobileOpen(!mobileOpen)} className="p-2 rounded-md hover:bg-accent">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {mobileOpen
              ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
          </svg>
        </button>
        <h1 className="text-sm font-bold text-primary">ETF 回测平台</h1>
        <button onClick={() => window.print()} className="p-2 rounded-md hover:bg-accent" title="导出PDF">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
          </svg>
        </button>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-40 bg-black/50" onClick={() => setMobileOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`w-56 border-r border-border bg-card h-screen sticky top-0 flex flex-col
        fixed lg:static z-50 transition-transform duration-200
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
        <div className="p-4 border-b border-border lg:block hidden">
          <h1 className="text-lg font-bold text-primary">ETF 回测平台</h1>
          <p className="text-xs text-muted-foreground mt-1">量化策略 · 资产配置</p>
        </div>
        <nav className="flex-1 overflow-y-auto p-2 mt-14 lg:mt-0">
          {navItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
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
        <div className="p-3 border-t border-border text-xs text-muted-foreground flex items-center justify-between">
          <span>v2.0 · Next.js 16</span>
          <button onClick={() => window.print()} className="hover:text-primary" title="打印/PDF">
            🖨️
          </button>
        </div>
      </aside>
    </>
  );
}
