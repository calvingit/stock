import type { Metadata } from 'next';
import { Sidebar } from '@/components/layout/Sidebar';
import './globals.css';

export const metadata: Metadata = {
  title: 'ETF 策略回测平台',
  description: '量化回测 · 资产配置 · 策略分析',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className="dark">
      <body>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 p-6 overflow-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
