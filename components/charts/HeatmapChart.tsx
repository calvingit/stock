'use client';

import { useEffect, useRef, useCallback } from 'react';
import { echarts } from './echarts-core';

interface HeatmapChartProps {
  data: [number, number, number][]; // [x, y, value]
  xLabels: string[];
  yLabels: string[];
  title?: string;
  height?: number;
  colorRange?: [string, string];
}

export function HeatmapChart({ data, xLabels, yLabels, title = '热力图', height = 300, colorRange = ['#22c55e', '#ef4444'] }: HeatmapChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof echarts.init>>(null);

  const renderChart = useCallback(() => {
    if (!containerRef.current) return;
    if (!chartRef.current) {
      chartRef.current = echarts.init(containerRef.current, 'dark');
    }

    chartRef.current.setOption({
      backgroundColor: 'transparent',
      title: { text: title, textStyle: { fontSize: 12, fontWeight: 'normal' }, left: 'center' },
      tooltip: { formatter: (p: unknown) => { const params = p as { data: [number, number, number] }; return `${yLabels[params.data[1]]} × ${xLabels[params.data[0]]}<br/>值: ${params.data[2]}`; } },
      grid: { left: 80, right: 40, top: 40, bottom: 50 },
      xAxis: { type: 'category', data: xLabels, splitArea: { show: true }, axisLabel: { fontSize: 10 } },
      yAxis: { type: 'category', data: yLabels, splitArea: { show: true }, axisLabel: { fontSize: 10 } },
      visualMap: {
        min: Math.min(...data.map((d) => d[2])),
        max: Math.max(...data.map((d) => d[2])),
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: { color: [colorRange[0], '#fbbf24', colorRange[1]] },
      },
      series: [{
        type: 'heatmap',
        data,
        label: { show: true, fontSize: 10 },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' } },
      }],
    });
  }, [data, xLabels, yLabels, title, colorRange]);

  useEffect(() => {
    renderChart();
    const handleResize = () => chartRef.current?.resize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [renderChart]);

  return <div ref={containerRef} style={{ width: '100%', height }} />;
}
