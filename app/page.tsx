import Link from 'next/link';

const strategies = [
  { href: '/ma-crossover', icon: '📈', title: '均线多头策略', desc: 'MA5/15/50 金叉 + 移动止损 + 大盘择时' },
  { href: '/multi-strategy', icon: '🔄', title: '多策略对比', desc: '并排比较多种策略的回测表现' },
  { href: '/band-strategy', icon: '📉', title: '波段策略', desc: '捕捉价格波动的短期机会' },
  { href: '/rsi-trend', icon: '📊', title: 'RSI 趋势跟踪', desc: 'RSI 上穿 50 追入 + 移动止损让利润奔跑' },
  { href: '/industry-rotation', icon: '🏭', title: '行业轮动', desc: '申万行业 ETF 轮动 + CSI300 择时' },
  { href: '/asset-allocation', icon: '🏛️', title: '资产配置', desc: '纳指 + 政金债 + 黄金 + 红利低波' },
  { href: '/buy-timing', icon: '🎯', title: '右侧买入时机', desc: '趋势确认信号 + RSI 突破' },
];

export default function Dashboard() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-2">策略超市</h2>
      <p className="text-muted-foreground mb-6">选择量化策略，基于历史数据进行回测分析</p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {strategies.map((s) => (
          <Link
            key={s.href}
            href={s.href}
            className="block p-5 rounded-lg border border-border hover:border-primary bg-card hover:bg-accent transition-all"
          >
            <div className="text-3xl mb-3">{s.icon}</div>
            <h3 className="text-lg font-semibold mb-1">{s.title}</h3>
            <p className="text-sm text-muted-foreground">{s.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
