interface StatItem {
  label: string;
  value: string;
  color?: string;
}

interface ResultSummaryProps {
  stats: StatItem[];
}

export function ResultSummary({ stats }: ResultSummaryProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {stats.map((stat, i) => (
        <div key={i} className="p-3 rounded-lg border border-border bg-card">
          <div className="text-xs text-muted-foreground">{stat.label}</div>
          <div className={`text-lg font-bold mt-1 ${stat.color || 'text-foreground'}`}>
            {stat.value}
          </div>
        </div>
      ))}
    </div>
  );
}
