# ETF 策略回测平台 — E2E 测试报告 & 待办事项

**日期**: 2026-07-01  
**测试地址**: https://stock.zhangwen.site/  
**测试方法**: 浏览器逐页访问 + API 端到端验证

---

## 一、页面测试结果

### ✅ 正常页面

| 页面 | 路由 | 状态 | 关键数据 |
|---|---|---|---|
| Dashboard | `/` | ✅ | 6 张策略卡片渲染正确 |
| 均线多头 | `/ma-crossover` | ✅ | 18.4% / -21.2% / 夏普 0.11 / 25 次 + 图表 |
| 行业轮动 | `/industry-rotation` | ✅ 已修复 | -6.1% / -44.6% / 116 次 / 31% 胜率 + 图表 |
| 多策略对比 | `/multi-strategy` | ✅ | 3 组参数对比表 + 叠加曲线 |
| 波段策略 | `/band-strategy` | ✅ | 29.7% / -22.0% / 夏普 0.15 + 图表 |

### ⚠️ 待验证页面

| 页面 | 路由 | 状态 | 说明 |
|---|---|---|---|
| RSI 趋势 | `/rsi-trend` | 🔧 已修复，待验证 | 重写为调用 `/api/backtest/rsi_trend` |
| 资产配置 | `/asset-allocation` | 🔧 已修复，待验证 | 添加自动运行 + 懒加载 plane/frontier |
| 右侧买入 | `/buy-timing` | ❌ 未测试 | — |
| 策略超市 | `/strategy-supermarket` | ❌ 未测试 | — |

---

## 二、已修复问题

### 2.1 行业轮动 400 错误
- **根因**: 前端调用 `/api/backtest`（通用 ETF 策略端点），但行业轮动有独立端点 `/api/backtest/industry_rotation`，参数完全不同
- **修复**: 重写 `app/industry-rotation/page.tsx`，直接调用正确端点，解析 `{mode, params, result}` 格式

### 2.2 RSI 趋势 0.0% 空数据
- **根因**: 同样调用 `/api/backtest`，而 RSI 策略需 `/api/backtest/rsi_trend?codes=159941&rsi_period=14&rsi_threshold=50`
- **修复**: 重写 `app/rsi-trend/page.tsx`，调用正确端点

### 2.3 资产配置不自动运行
- **根因**: 页面改为懒加载后未在挂载时触发回测
- **修复**: `runAllocation` 用 `useCallback` 包装 + `useEffect` 自动触发

### 2.4 前端 API 调用架构
- **修复**: 导出 `fetchAPI` 从 `lib/api.ts`，供独立策略页面直接调用专用端点
- **代理路径**: `/api/api/{path}` → Next.js catch-all → `http://127.0.0.1:8899/api/{path}`

---

## 三、待办事项（按优先级）

### P0 — 功能正确性
- [ ] 验证 RSI 趋势页面修复后数据正确显示（预期: 65.66% / -24.15% / 夏普 0.41 / 7 次）
- [ ] 验证资产配置页面首次加载自动运行且速度正常
- [ ] 测试 `buy-timing` 页面渲染
- [ ] 测试 `strategy-supermarket` 页面渲染

### P1 — 性能优化
- [ ] 分析 `/api/backtest` 策略页面首次加载慢的根因（Wind 拉取 vs 计算）
- [ ] 策略页面后端结果缓存（目前仅 asset_allocation 有缓存）
- [ ] 前端 SWR/stale-while-revalidate 策略减少重复请求

### P2 — 移动端适配验证
- [ ] 手机视口下汉堡菜单滑入/滑出
- [ ] 图表在移动端宽度自适应
- [ ] 统计卡片在移动端 2 列布局

### P3 — 组件集成
- [ ] HeatmapChart（月度收益/相关性热力图）集成到策略详情页
- [ ] TradeTable（交易记录可排序/筛选/CSV导出）集成
- [ ] ResultSummary 统计卡片组件集成

### P4 — 长期
- [ ] 旧前端 `templates/index.html` 退役
- [ ] E2E 自动化测试脚本（Playwright）
- [ ] CI/CD 自动部署

---

## 四、后端缓存现状

| 端点 | 缓存 | 命中后耗时 |
|---|---|---|
| `/api/asset_allocation/gradient` | ✅ 后端 TTL 1hr + 启动预热 | ~11ms |
| `/api/asset_allocation/plane` | ✅ 后端 TTL 1hr + 启动预热 | ~11ms |
| `/api/asset_allocation/frontier` | ✅ 后端 TTL 1hr（随机权重命中率低） | ~11ms (命中) / ~7s (未命中) |
| `/api/backtest` (通用 ETF) | ❌ 无缓存 | ~250ms |
| `/api/backtest/industry_rotation` | ❌ 无缓存 | ~500ms |
| `/api/backtest/rsi_trend` | ❌ 无缓存 | ~200ms |
| `/api/backtest/band` | ❌ 无缓存 | ~200ms |
| Next.js 代理层 | ✅ LRU 5min + 120s 超时 | 命中后 ~5ms |

---

## 五、关键架构信息

- **前端**: ~/stock-web/ — Next.js 16.2.9 + React 19 + TS6 + ECharts 6 + Tailwind 4 + pnpm 11
- **后端**: ~/etf-backtest/ — FastAPI :8899 (systemd)
- **代理**: Caddy (stock.zhangwen.site) → :3001 Next.js → :8899 FastAPI
- **Wind 数据**: `node scripts/cli.mjs call fund_data get_fund_kline`（24hr 文件缓存）
- **ETF 代码**: 159941.SZ(纳指100)、515100.SH(红利低波100)、511580.SH(政金债)、518880.SH(黄金)
- **共同回测区间**: 2022-12-14 ~ 2026-06-30
