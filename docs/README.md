# 项目文档导航

本文档是 `docs/` 目录入口，用于帮助新同事和后续 Agent 快速判断“先读哪一份、哪一份是历史台账、哪一份是最新结论”。

## 推荐阅读顺序

1. `总体架构说明_同事版_2026-06-17.md`：理解产品预期、双阶段流程、三档产品和合规边界。
2. `推广老师沟通说明_2026-06-24.md`：面向推广老师、招生转化和家长沟通，快速了解系统功能、宣传口径和合规边界。
3. `2026-06-23-structured-report-export-design.md` / `2026-06-23-structured-report-export-implementation-plan.md`：理解最新结构化 PDF / Word 导出能力。
4. `重构执行与架构对齐记录_2026-06-18.md`：理解第一轮重构如何对齐架构，以及 Step 5A-5C 的结果。
5. `refactor_execution_update_2026-06-18.md`：理解 ReportsPage、admissions_engine 和首次进入产品流改造。
6. `系统目标差距分析.md`、`志愿报告功能差距分析.md`：理解当前系统与商业化目标之间的剩余差距。
7. 数据类台账：确认真实数据覆盖、导入和恢复方式。

## 架构与目标

| 文档 | 用途 | 当前定位 |
|---|---|---|
| `总体架构说明_同事版_2026-06-17.md` | 同事提供的预期总体架构说明 | 产品与架构参考基线 |
| `推广老师沟通说明_2026-06-24.md` | 给推广老师讲清楚系统功能、演示路线、宣传话术和禁止承诺 | 当前推广沟通入口 |
| `系统目标差距分析.md` | 系统目标、现状和差距 | 历史差距分析，仍可参考 |
| `志愿报告功能差距分析.md` | 志愿报告能力缺口 | 报告产品完善参考 |
| `数据整理与正式版落地清单.md` | 正式版落地前的数据与产品清单 | 交付准备参考 |

## 最新产品化设计

| 文档 | 用途 | 当前定位 |
|---|---|---|
| `superpowers/specs/2026-06-22-metaphysics-engine-design.md` | 精确四柱 / 命理画像引擎设计 | 画像引擎 Phase 1 设计依据 |
| `superpowers/plans/2026-06-22-metaphysics-engine-implementation-plan.md` | 命理画像引擎实施计划 | 已执行的 Phase 1 计划记录 |
| `superpowers/specs/2026-06-23-structured-report-export-design.md` | 7 列结构化正式报告导出设计 | PDF / Word 推荐表导出依据 |
| `superpowers/plans/2026-06-23-structured-report-export-implementation-plan.md` | 结构化报告导出实施计划 | 已执行的导出升级计划记录 |

## 重构与执行记录

| 文档 | 用途 | 当前定位 |
|---|---|---|
| `重构执行与架构对齐记录_2026-06-18.md` | 记录 Step 5A-5C 的拆包、页面拆分和招生上下文拆分 | 第一轮架构对齐记录 |
| `refactor_execution_update_2026-06-18.md` | 记录 Step 6A-8 的报告页拆分、招生引擎拆分和首次进入产品流 | 最新重构结论 |

## 数据与数据库

| 文档 | 用途 | 当前定位 |
|---|---|---|
| `PostgreSQL真实数据导入执行记录_2026-06-10.md` | PostgreSQL 真实数据导入记录 | 历史导入台账 |
| `PostgreSQL真实数据核验台账_2026-06-10.md` | PostgreSQL 数据核验记录 | 历史核验台账 |
| `目标省份真实数据覆盖核验_2026-06-12.md` | 目标省份数据覆盖检查 | 省份数据覆盖参考 |
| `数据库备份与同事恢复说明.md` | 数据库备份与恢复说明 | 协作恢复指南 |
| `province_batches批次判断逻辑校验执行记录_2026-06-13.md` | 批次判断逻辑校验记录 | 批次线逻辑参考 |

## 规则与政策数据

| 文档 | 用途 | 当前定位 |
|---|---|---|
| `admission_risk_rules扩充执行记录_2026-06-12.md` | 录取风险规则扩充记录 | 规则库历史台账 |
| `institution_rules扩充执行记录_2026-06-13.md` | 院校规则扩充记录 | 规则库历史台账 |
| `policy_trends扩充执行记录_2026-06-13.md` | 政策趋势扩充记录 | 政策数据历史台账 |

## 最新质量门禁

默认提交业务代码前执行：

```bash
npm run test:backend
npm run test:product-flow
npm run lint
npm run build
npm run test:frontend:error-states
```

其中 `npm run test:product-flow` 用于防止“入口引导/画像分析 -> 分数换算 -> 正式推荐报告”的首次进入产品流顺序被误改。

交付前建议额外执行：

```bash
npm run test:product-flow:e2e
```

该命令用本地 mock API 和真实浏览器验证首次进入产品流 happy path，不依赖远程数据库或 `data_assets/`。
