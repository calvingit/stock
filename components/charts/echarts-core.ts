'use client';

import { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { LineChart, ScatterChart, HeatmapChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
  MarkPointComponent,
  MarkLineComponent,
  VisualMapComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

// Register only needed components (tree-shaking)
echarts.use([
  LineChart,
  ScatterChart,
  HeatmapChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
  MarkPointComponent,
  MarkLineComponent,
  VisualMapComponent,
  CanvasRenderer,
]);

export { echarts };
export type EChartsType = echarts.ECharts;
