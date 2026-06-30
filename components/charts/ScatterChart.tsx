'use client';

import { useEffect, useRef, useCallback } from 'react';
import { echarts } from './echarts-core';

interface ScatterChartProps {
  data: { x: number; y: number; name?: string; itemStyle?: Record<string, unknown> }[];
  xLabel: string;
  yLabel: string;
  title?: string;
  height?: number;
  highlightIndex?: number;
}

export function ScatterChart({ data, xLabel, yLabel, title = '散点图', height = 350, highlightIndex }: ScatterChartProps) {
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
      tooltip: {
        formatter: (p: unknown) => {
          const params = p as { data: { x: number; y: number; name?: string } };
          return `${params.data.name || ''}<br/>${xLabel}: ${params.data.x.toFixed(2)}<br/>${yLabel}: ${params.data.y.toFixed(2)}`;
        },
      },
      grid: { left: 60, right: 40, top: 40, bottom: 50 },
      xAxis: { name: xLabel, nameLocation: 'middle', nameGap: 30, splitLine: { show: true, lineStyle: { color: '#333' } } },
      yAxis: { name: yLabel, nameLocation: 'middle', nameGap: 40, splitLine: { show: true, lineStyle: { color: '#333' } } },
      series: [{
        type: 'scatter',
        data: data.map((d, i) => ({
          value: [d.x, d.y],
          name: d.name,
          itemStyle: i === highlightIndex
            ? { color: '#f59e0b', borderColor: '#fff', borderWidth: 2, shadowBlur: 10 }
            : d.itemStyle || { color: '#60a5fa', opacity: 0.7 },
        })),
        symbolSize: (d: unknown) => {
          const vals = d as [number, number];
          return vals[1] && Math.abs(vals[1]) > 0.2 ? 12 : 7;
        },
        emphasis: { scale: 1.5 },
      }],
    });
  }, [data, xLabel, yLabel, title, highlightIndex]);

  useEffect(() => {
    renderChart();
    const handleResize = () => chartRef.current?.resize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [renderChart]);

  return <div ref={containerRef} style={{ width: '100%', height }} />;
}
