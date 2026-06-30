'use client';

import { useEffect, useRef, useCallback } from 'react';
import { echarts } from './echarts-core';

interface EquityChartProps {
  data: [string, number][];
  title?: string;
  height?: number;
  marks?: { date: string; price: number; type: 'buy' | 'sell'; label?: string }[];
  overlay?: { data: [string, number][]; name: string }[];
}

export function EquityChart({ data, title = '净值曲线', height = 400, marks = [], overlay = [] }: EquityChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof echarts.init>>(null);

  const renderChart = useCallback(() => {
    if (!containerRef.current) return;

    if (!chartRef.current) {
      chartRef.current = echarts.init(containerRef.current, 'dark');
    }

    const dates = data.map((d) => d[0]);
    const values = data.map((d) => d[1]);

    const markData = marks.map((m) => ({
      coord: [m.date, m.price],
      symbol: m.type === 'buy' ? 'triangle' : 'pin',
      symbolSize: m.type === 'buy' ? 12 : 14,
      itemStyle: { color: m.type === 'buy' ? '#22c55e' : '#ef4444' },
      label: {
        show: true,
        formatter: m.label || m.type.toUpperCase(),
        position: m.type === 'buy' ? 'bottom' : 'top',
        fontSize: 9,
        color: m.type === 'buy' ? '#22c55e' : '#ef4444',
      },
    }));

    const series: object[] = [
      {
        name: '净值',
        type: 'line',
        data: values,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: '#3b82f6' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(59,130,246,0.3)' },
            { offset: 1, color: 'rgba(59,130,246,0.02)' },
          ]),
        },
        markPoint: { data: markData },
      },
      ...overlay.map((o) => ({
        name: o.name,
        type: 'line',
        data: o.data.map((d: [string, number]) => d[1]),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.5, type: 'dashed' },
      })),
    ];

    chartRef.current.setOption({
      backgroundColor: 'transparent',
      title: { text: title, textStyle: { fontSize: 14, fontWeight: 'normal' }, left: 'center' },
      tooltip: { trigger: 'axis' },
      grid: { left: 60, right: 30, top: 50, bottom: 60 },
      legend: { show: overlay.length > 0, bottom: 0 },
      xAxis: { type: 'category', data: dates, boundaryGap: false },
      yAxis: { type: 'value', scale: true, axisLabel: { formatter: '{value}x' } },
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 25 }],
      series,
    });
  }, [data, title, marks, overlay]);

  useEffect(() => {
    renderChart();
    const handleResize = () => chartRef.current?.resize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [renderChart]);

  return <div ref={containerRef} style={{ width: '100%', height }} />;
}
