'use client';

import { useEffect, useRef, useCallback } from 'react';
import { echarts } from './echarts-core';

interface DrawdownChartProps {
  data: [string, number][];
  title?: string;
  height?: number;
}

export function DrawdownChart({ data, title = '回撤曲线', height = 200 }: DrawdownChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof echarts.init>>(null);

  const renderChart = useCallback(() => {
    if (!containerRef.current) return;
    if (!chartRef.current) {
      chartRef.current = echarts.init(containerRef.current, 'dark');
    }

    const dates = data.map((d) => d[0]);
    const values = data.map((d) => d[1]);

    chartRef.current.setOption({
      backgroundColor: 'transparent',
      title: { text: title, textStyle: { fontSize: 12, fontWeight: 'normal' }, left: 'center', top: 5 },
      grid: { left: 50, right: 20, top: 40, bottom: 40 },
      tooltip: { trigger: 'axis', formatter: (params: unknown) => { const p = params as { axisValue: string; value: number }[]; return `${p[0].axisValue}<br/>回撤: ${(p[0].value * 100).toFixed(2)}%`; } },
      xAxis: { type: 'category', data: dates, boundaryGap: false, axisLabel: { show: false } },
      yAxis: { type: 'value', axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 15, bottom: 15 }],
      series: [{
        type: 'line',
        data: values,
        showSymbol: false,
        lineStyle: { width: 1, color: '#ef4444' },
        areaStyle: { color: 'rgba(239,68,68,0.25)' },
      }],
    });
  }, [data, title]);

  useEffect(() => {
    renderChart();
    const handleResize = () => chartRef.current?.resize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [renderChart]);

  return <div ref={containerRef} style={{ width: '100%', height }} />;
}
