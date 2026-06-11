# TASKS

## 使用规则

这份文档只保留一套可持续维护的结构：

1. `当前执行清单`
   这是唯一需要持续勾选状态的地方，也是当前迭代的唯一进度源。
2. `产品定义`
   说明 99 / 399 / 999 当前已落地档位，以及 699 / 999 深度档位目标边界，不在这里重复维护开发状态。
3. `阶段路线图`
   说明后续按什么顺序推进，不在这里重复勾选完成情况。
4. `项目台账`
   保留当前快照、数据状态、工程风险和长期事项，作为背景资料。

维护原则：

- 不再在多个章节重复维护同一条任务状态。
- 只在 `当前执行清单` 勾选状态。
- 其余章节只表达范围、目标、背景和顺序。

---

## 项目目标

本项目不是单纯查询分数线的工具，而是一个可交付、可解释、可售卖的高考志愿决策辅助系统。

目标主链路：

`录入学生信息 -> 生成辅助画像 -> 给出专业方向 -> 匹配城市/院校/专业 -> 选择报告版本 -> 生成并下载报告`

边界要求：

- 前六字、八字四柱、星座、五行、性格标签等内容只能作为解释层，不能替代真实招生数据。
- 分数、位次、选科要求、招生计划、历史录取数据、章程和政策规则必须作为硬判断依据。
- 所有结果都必须有风险提示，禁止出现“保录”“必中”“100%录取”等承诺性表达。

---

## 当前结论

当前系统已经具备“学生录入 + 分析页面 + 报告页面 + 基础导出”的壳，但还不能视为“真实招生数据驱动的正式志愿交付系统”。

这次按当前运行时 PostgreSQL 实际核查后的结论是：

- 已有真实学生录入链路和主流程入口，主导航已收敛到 `dashboard / students / intake / reports`。
- 已有结构化推荐结果接口形态：`recommendationTable`、`firstChoice`、`alternatives`、`notRecommended`。
- 报告页面已经能展示结构化推荐结果。
- PDF / DOCX 真导出链路已经可用，并且会写入 `report_delivery_records` 留痕。
- 数据库运行时已经切到 PostgreSQL-only。
- 但当前连接的 PostgreSQL 中，`institutions`、`majors`、`admission_plans`、`institution_admission_scores`、`major_admission_scores`、`subject_requirements`、`admission_risk_rules`、`policy_trends`、`province_batches` 仍是空表，系统当前无法稳定命中真实招生候选。

当前最需要正视的不是“页面还不够多”，而是“真实数据链路、正式导出链路、下载链路和产品口径都还没有收口”。

当前最大的 6 个缺口：

1. 当前 PostgreSQL 真实招生表为空，系统会大量退回画像/规则兜底结果，而不是正式招生结果。
2. 前端没有清楚区分“真实招生推荐”和“fallback 推荐”，容易让使用者误判结果可信度。
3. `backend/report_exporters.py` 还没有把结构化推荐表正式导出到 PDF / DOCX，只是在导出段落内容。
4. 当前导出返回的是服务器本地文件路径，不是真正的下载链路。
5. 产品版本口径不一致，页面文案里仍出现 `699`，但当前代码正式产品配置只有 `99 / 399 / 999`。
6. `src/pages/SettingsPage.vue` 仍然是占位页，缺少正式系统最小可用的配置能力。

---

## 当前执行清单

### 已完成

#### 产品流程

- [x] 将学生详情页改造成核心业务入口
- [x] 在学生详情页展示当前流程进度
- [x] 每一步显示“下一步操作”提示
- [x] 工作台快捷入口只保留核心流程
- [x] 弱化主导航中的演示型入口

#### 推荐结果接入

- [x] `backend/admissions_engine.py` 产出结构化推荐结果
- [x] `backend/planning_repository.py` 将结构化推荐结果接入正式报告 JSON
- [x] `src/pages/ReportsPage.vue` 展示院校专业推荐表、第一志愿、备选志愿、不建议项

#### 导出基础链路

- [x] `backend/report_exporters.py` 能生成真实 `.pdf` 文件
- [x] `backend/report_exporters.py` 能生成真实 `.docx` 文件
- [x] `backend/planning_repository.py` 已接好正式导出产物落盘与留痕
- [x] `backend/main.py` 已提供 PDF / Word 导出 API

#### 数据底座

- [x] PostgreSQL 已成为唯一运行时数据库入口

### P0

#### 真实招生数据链路

- [x] 核验当前 PostgreSQL 连接的真实数据状态，并形成书面台账
- [x] 补齐 `institutions`
- [x] 补齐 `majors`
- [x] 补齐 `admission_plans`
- [x] 补齐 `institution_admission_scores`
- [x] 补齐 `major_admission_scores`
- [x] 补齐 `subject_requirements`
- [x] 补齐 `province_batches`
- [x] 补齐 `institution_rules`
- [x] 补齐 `admission_risk_rules`
- [x] 补齐 `policy_trends`
- [x] 验证 `backend/planning_repository.py` 的报告链路已能稳定命中真实候选，而不是 fallback 分支

#### 结果可信度标识

- [x] 在后端响应中增加“真实招生结果 / fallback 结果”标记
- [x] `src/pages/AnalysisPage.vue` 明确展示当前结果来源
- [x] `src/pages/MajorsPage.vue` 明确展示当前结果来源
- [x] `src/pages/PlanPage.vue` 明确展示当前结果来源
- [x] `src/pages/ReportsPage.vue` 明确展示当前结果来源
- [x] 当未命中真实招生数据时，统一显示醒目的风险提示和后续操作建议

#### 报告导出正式化

- [x] `backend/report_exporters.py` 接入结构化推荐表导出
- [x] PDF 中展示清晰的冲 / 稳 / 保推荐表
- [ ] DOCX 中展示清晰的冲 / 稳 / 保推荐表
- [ ] 导出中展示专业组/代码、最低分、最低位次、位次差、风险等级、推荐理由
- [ ] 导出中补齐调剂风险、选科限制、计划变化风险、热门专业风险提示
- [ ] 导出中补齐第一志愿、备选志愿、不建议报考项

#### 下载链路

- [ ] 增加正式下载接口，而不是只返回服务器本地文件路径
- [ ] 前端点击“导出 PDF / Word”后可直接下载文件
- [ ] 导出记录页优先展示可访问的下载入口，而不只是磁盘路径
- [ ] 核验桌面联调和浏览器访问两种场景下的下载行为一致性

#### 测试稳定性

- [ ] 将 `backend/tests/test_report_export.py` 拆成“纯 exporter 单测”和“最小集成测试”
- [ ] 移除 exporter 单测对 `planning_repository` 的直接依赖
- [ ] 导出单测统一使用最小 mock `report_data`
- [ ] 单个测试文件命令统一加超时约束，确保不会长时间卡住
- [ ] 建立导出链路最小回归测试

#### 产品口径

- [ ] 统一当前正式产品版本口径为一套可执行定义
- [ ] 修正工作台中的 `99 / 399 / 699 / 999` 文案
- [ ] 修正学生详情页中的 `99 / 399 / 699 / 999` 文案
- [ ] 修正报告页、文档、产品说明中的版本描述
- [ ] 明确 `699` 是暂不支持还是立即补做

#### 合规边界

- [ ] 统一报告页、导出报告、顾问话术中的免责声明
- [ ] 检查是否存在容易被理解为“保录”“必中”的表述
- [ ] 保持画像层只用于解释，不覆盖真实录取判断

### P1

#### 数据层补强

- [ ] 明确当前“正式支持省份”清单
- [ ] 核验浙江等目标省份是否已有与河南同等级别的真实招生数据
- [ ] 扩充 `admission_risk_rules`
- [ ] 扩充 `institution_rules`
- [ ] 扩充 `policy_trends`
- [ ] 补齐 `province_batches` 后校验批次判断逻辑
- [x] 建立真实数据导入后的最小验收脚本

#### 前端稳定性

- [ ] 清理关键链路中的静默 mock 回退
- [ ] 明确哪些接口允许 demo fallback，哪些接口必须真实报错
- [ ] 在学生录入、画像推导、报告生成链路上优先关闭静默 fallback
- [ ] 前端接口失败时显示可执行的错误提示，而不是继续展示假数据

#### 设置页最小可用化

- [ ] 为 `src/pages/SettingsPage.vue` 增加真实可用的配置项
- [ ] 增加默认顾问署名配置
- [ ] 增加合规文案配置
- [ ] 增加报告导出基础配置
- [ ] 增加产品版本开关或展示配置
- [ ] 保持设置页只做“最小可用后台”，不扩成大而全系统

#### 产品价值提升

- [ ] 建立本地专业解释库：具体专业、课程难点、适合人群、就业方向、考研方向
- [ ] 建立本地城市解释库：产业优势、就业机会、生活成本、迁移路径
- [ ] 建立本地画像映射库：性格/兴趣标签到专业方向的解释模板
- [ ] 建立报告话术库：推荐理由、风险提示、家长沟通建议、合规提醒
- [ ] 在报告中区分“数据依据”和“解释依据”

#### 399 元正式交付增强

- [ ] 把城市产业解释落到具体专业和职业路径
- [ ] 把家长沟通建议做成结构化区块，而不只是段落
- [ ] 增加决策优先级建议：专业优先 / 学校优先 / 城市优先
- [ ] 增加调剂接受度说明与建议

#### 工程治理

- [ ] 清理仍保留在代码中的 demo / fallback / legacy 说明
- [ ] 统一 README 和项目文档中的数据库表述
- [ ] 统一 `99 / 399 / 999 / 699` 的产品口径，避免“文档有 699、代码无 699 配置”的错位
- [ ] 给 `data_assets/generated_reports/` 增加明确的产物管理规则，并处理历史 `.html` / `.md` / `.pdf` / `.docx` 混存问题
- [ ] 清理仓库中的 SQLite 痕迹与过时忽略规则

### P2

#### 699 / 999 深度报告

- [ ] 名校优先 / 专业优先 / 城市优先三套方案
- [ ] 多方案对比页
- [ ] 考研路径分析
- [ ] 就业城市迁移路径
- [ ] 家庭预算、距离、是否出省等约束条件分析
- [ ] 顾问人工复核入口和复核字段

#### 长期架构

- [ ] 评估是否需要把本地解释库升级为向量库 / RAG
- [ ] 规划后台权限、日志、备份、恢复和运维能力
- [ ] 建立更完整的前后端自动化回归体系

### 当前执行顺序

1. 打通当前 PostgreSQL 的真实招生数据链路
2. 区分“真实招生结果”和“fallback 结果”
3. `backend/report_exporters.py` 结构化推荐表导出
4. 正式下载链路
5. `backend/tests/test_report_export.py` 单测/集成拆分与超时约束
6. 统一产品版本口径
7. 本地专业 / 城市 / 画像解释库
8. 699 / 999 深度版能力

---

## 产品定义

### 当前代码已落地档位

- `99`：基础版
- `399`：进阶版
- `999`：人工咨询版底稿

说明：

- 当前代码里的正式产品配置是 `99 / 399 / 999`。
- `699` 目前仍属于产品目标口径，尚未落到 `backend/planning_repository.py` 的正式产品配置中。

### 99 元基础版

定位：

- 基础认知版
- 适合先做方向判断和家长沟通铺垫

应包含：

- 学生基础信息
- 分数 / 位次分析
- 画像解释
- 专业大方向
- 城市方向
- 基础风险提示

### 399 元标准版

定位：

- 真正可售卖的标准志愿方案

应包含：

- 99 元全部内容
- 具体院校 + 专业 + 专业组/代码推荐表
- 冲 / 稳 / 保梯度
- 第一志愿建议
- 备选志愿建议
- 不建议方向
- 调剂风险、选科限制、计划变化风险、热门专业风险提示
- 可下载的正式 PDF / DOCX 报告

### 699 / 999 元深度版

定位：

- 深度咨询交付版

应包含：

- 399 元全部内容
- 名校优先 / 专业优先 / 城市优先三套方案
- 考研路径分析
- 就业路径和城市迁移路径
- 家庭预算 / 距离 / 是否出省等约束条件建议
- 顾问人工复核建议

---

## 阶段路线图

### 阶段 1：项目盘点

目标：

- 识别真实业务页面与演示页面
- 确认真实推荐逻辑、报告逻辑、导出逻辑所在文件
- 核验真实数据是否真的已入库

已产出：

- `docs/志愿报告功能差距分析.md`
- `docs/系统目标差距分析.md`

执行清单（文件 / 命令）：

1. 盘点前端页面和路由入口
文件：
- `src/router/index.js`
- `src/App.vue`
- `src/pages/*.vue`
命令：
```powershell
rg --files src/pages
Get-Content src/router/index.js -Encoding utf8
Get-Content src/App.vue -Encoding utf8
```
验收：
- 明确哪些页面属于主流程，哪些页面属于 demo / base-data / settings / 占位页。

2. 盘点后端正式链路入口
文件：
- `backend/main.py`
- `backend/planning_repository.py`
- `backend/admissions_engine.py`
- `backend/report_exporters.py`
命令：
```powershell
rg -n "FastAPI|@app.get|@app.post|def get_student_|def export_report_package" backend
rg -n "def match_admissions_candidates|def build_plan_columns_from_candidates|def export_report_pdf|def export_report_docx" backend
```
验收：
- 明确分析、专业、志愿、报告、导出分别由哪些函数负责。

3. 盘点数据库运行时状态
文件：
- `backend/database.py`
- `.env`
命令：
```powershell
Get-Content backend/database.py -Encoding utf8
Get-Content .env -Encoding utf8
```
```powershell
@'
from backend.database import db_session
tables = [
    "students","scores","institutions","majors","province_batches",
    "admission_plans","institution_admission_scores","major_admission_scores",
    "subject_requirements","institution_rules","admission_risk_rules","policy_trends"
]
with db_session() as conn:
    for table in tables:
        total = conn.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()["total"]
        print(table, total)
'@ | .\.venv\Scripts\python.exe -
```
验收：
- 形成一份当前 PostgreSQL 实际数据台账，并与文档保持一致。

4. 盘点导入脚本和历史文档
文件：
- `backend/scripts/*.py`
- `docs/*.md`
命令：
```powershell
rg --files backend/scripts
rg --files docs
```
验收：
- 明确哪些脚本负责数据导入，哪些文档可作为后续修订依据。

### 阶段 2：收敛主流程入口

目标：

- 从“很多页面”收敛为“一条主业务流程”

当前状态：

- 已完成

执行清单（文件 / 命令）：

1. 复核主导航是否只保留主流程
文件：
- `src/App.vue`
- `src/data/mock.js`
命令：
```powershell
Get-Content src/App.vue -Encoding utf8
Get-Content src/data/mock.js -Encoding utf8
```
验收：
- 主导航默认只暴露 `dashboard / students / intake / reports`。

2. 复核工作台是否只引导主链路
文件：
- `src/pages/DashboardPage.vue`
命令：
```powershell
Get-Content src/pages/DashboardPage.vue -Encoding utf8
```
验收：
- 工作台只强调“新增学生 / 继续处理学生 / 生成正式报告”。

3. 复核学生详情页是否承担流程工作台角色
文件：
- `src/pages/StudentDetailPage.vue`
命令：
```powershell
Get-Content src/pages/StudentDetailPage.vue -Encoding utf8
```
验收：
- 学生详情页能显示步骤状态、下一步动作、报告版本入口。

4. 复核弱业务页面是否已降级
文件：
- `src/pages/DemoReportsPage.vue`
- `src/pages/BaseDataPage.vue`
- `src/pages/SettingsPage.vue`
命令：
```powershell
rg -n "演示报告|基础数据|系统设置|占位页|待完善" src/pages
```
验收：
- 弱业务页面不再占据主流程入口，且其定位说明清楚。

### 阶段 3：打通结构化推荐结果

目标：

- 后端产出正式推荐结果
- 报告页展示正式推荐结果

当前状态：

- 页面展示已完成
- 正式报告 JSON 已完成
- 真实招生数据未落库完成前，正式推荐结果仍可能退回 fallback
- 导出层结构化表格未完成

执行清单（文件 / 命令）：

1. 打通真实招生候选数据来源
文件：
- `backend/planning_repository.py`
- `backend/admissions_engine.py`
- `backend/admissions_repository.py`
命令：
```powershell
rg -n "def _get_real_admissions_bundle|def match_admissions_candidates|def build_admissions_context" backend
```
验收：
- 明确 `get_student_analysis / get_student_majors / get_student_plan / get_student_report` 何时走真实候选，何时走 fallback。

2. 导入真实招生核心数据
文件：
- `backend/scripts/import_*.py`
命令：
```powershell
rg --files backend/scripts
```
建议执行命令：
```powershell
.\.venv\Scripts\python.exe backend/scripts/import_foundation_data.py
.\.venv\Scripts\python.exe backend/scripts/import_province_batches.py
.\.venv\Scripts\python.exe backend/scripts/import_score_segments.py
.\.venv\Scripts\python.exe backend/scripts/import_subject_requirements.py
.\.venv\Scripts\python.exe backend/scripts/import_institution_rules.py
.\.venv\Scripts\python.exe backend/scripts/import_admission_plans.py
.\.venv\Scripts\python.exe backend/scripts/import_institution_admission_scores.py
.\.venv\Scripts\python.exe backend/scripts/import_major_admission_scores.py
```
验收：
- 核心招生表不再为空，且至少一省能产出真实候选。

3. 增加“真实结果 / fallback 结果”标识
文件：
- `backend/planning_repository.py`
- `src/pages/AnalysisPage.vue`
- `src/pages/MajorsPage.vue`
- `src/pages/PlanPage.vue`
- `src/pages/ReportsPage.vue`
命令：
```powershell
rg -n "hasStudent|ruleSummary|portraitRecommendation|recommendationTable|firstChoice" src/pages backend/planning_repository.py
```
验收：
- 页面能明确显示当前结果来源和风险级别。

4. 回归验证结构化推荐输出
文件：
- `backend/tests/test_admissions_engine.py`
- `backend/tests/test_planning_repository_structured_report.py`
命令：
```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_admissions_engine backend.tests.test_planning_repository_structured_report
```
验收：
- `recommendationTable`、`firstChoice`、`alternatives`、`notRecommended` 结构稳定。

### 阶段 4：完成正式导出

目标：

- PDF / DOCX 成为真正可交付的正式报告，而不是段落导出

当前状态：

- 真导出已完成
- 正式表格化交付未完成
- 正式下载链路未完成

执行清单（文件 / 命令）：

1. 把结构化推荐表写入 PDF / DOCX
文件：
- `backend/report_exporters.py`
- `backend/planning_repository.py`
命令：
```powershell
rg -n "recommendationTable|firstChoice|alternatives|notRecommended|sections|disclaimer" backend
```
验收：
- 导出文件中包含冲 / 稳 / 保表格、第一志愿、备选志愿、不建议项。

2. 增加正式下载接口
文件：
- `backend/main.py`
- `backend/planning_repository.py`
- `src/api/planning.js`
- `src/pages/ReportsPage.vue`
命令：
```powershell
rg -n "export/pdf|export/word|downloadUrl|artifact_path" backend src
```
验收：
- 前端点击导出后能直接下载文件，而不是只显示本地路径。

3. 拆分导出测试
文件：
- `backend/tests/test_report_export.py`
- `backend/report_exporters.py`
命令：
```powershell
Get-Content backend/tests/test_report_export.py -Encoding utf8
.\.venv\Scripts\python.exe -m unittest backend.tests.test_report_export
```
验收：
- 单测可独立覆盖 exporter，最小集成测试只保留一条。

4. 进行本地联调验证
文件：
- `package.json`
- `backend/scripts/start_backend.ps1`
- `backend/scripts/start_frontend.ps1`
命令：
```powershell
npm run dev
npm run dev:backend
```
验收：
- 在真实学生报告页中可生成、下载、留痕 PDF / Word。

### 阶段 5：补足数据与深度内容

目标：

- 打通真实数据底座
- 明确正式支持省份
- 补规则覆盖
- 补专业 / 城市 / 路径解释深度
- 打开 699 / 999 深度版能力

当前状态：

- 未完成

执行清单（文件 / 命令）：

1. 明确正式支持省份清单
文件：
- `backend/admissions_repository.py`
- `docs/*.md`
- `TASKS_updated_with_staged_tasks.md`
命令：
```powershell
@'
from backend.database import db_session
queries = {
    "institution_admission_scores": "SELECT province, COUNT(*) AS total FROM institution_admission_scores GROUP BY province ORDER BY total DESC",
    "major_admission_scores": "SELECT province, COUNT(*) AS total FROM major_admission_scores GROUP BY province ORDER BY total DESC",
    "subject_requirements": "SELECT province, COUNT(*) AS total FROM subject_requirements GROUP BY province ORDER BY total DESC",
    "province_batches": "SELECT province, COUNT(*) AS total FROM province_batches GROUP BY province ORDER BY total DESC"
}
with db_session() as conn:
    for name, sql in queries.items():
        print("---", name, "---")
        for row in conn.execute(sql).fetchall():
            print(row["province"], row["total"])
'@ | .\.venv\Scripts\python.exe -
```
验收：
- 文档里明确列出“已正式支持 / 部分支持 / 未支持”的省份清单。

2. 补强风险、规则、政策覆盖
文件：
- `backend/admissions_repository.py`
- `backend/scripts/import_institution_rules.py`
- `backend/scripts/import_henan_policy_rules.py`
命令：
```powershell
.\.venv\Scripts\python.exe backend/scripts/import_institution_rules.py
.\.venv\Scripts\python.exe backend/scripts/import_henan_policy_rules.py
```
验收：
- `institution_rules`、`admission_risk_rules`、`policy_trends` 有稳定可用数据。

3. 建设专业 / 城市 / 画像解释库
文件：
- `backend/foundation_repository.py`
- `data_assets/`
- `src/pages/ReportsPage.vue`
命令：
```powershell
rg -n "major_categories|city_industries|report_template_fields" backend data_assets src
```
验收：
- 报告里能区分“数据依据”和“解释依据”，并支撑 399 档交付深度。

4. 收口设置页和产品口径
文件：
- `src/pages/SettingsPage.vue`
- `src/pages/DashboardPage.vue`
- `src/pages/StudentDetailPage.vue`
- `src/pages/ReportsPage.vue`
- `backend/planning_repository.py`
命令：
```powershell
rg -n "699|999|99|399|设置模块待完善|占位页" src backend
```
验收：
- 设置页具备最小可用配置能力，产品版本文案全链路一致。

5. 回归验证阶段成果
文件：
- `backend/tests/*.py`
- `src/pages/*.vue`
命令：
```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_admissions_engine backend.tests.test_planning_repository_structured_report backend.tests.test_report_export
npm run build
```
验收：
- 后端核心测试通过，前端可构建，主流程可从学生录入走到正式报告导出。

---

## 项目台账

### 当前系统快照

- 真实学生链路已跑通。
- 当前运行时 PostgreSQL 中仍只有极少量学生数据，真实招生核心表尚未落库完成。
- 报告接口已能返回结构化推荐结果。
- 报告页面已接入结构化推荐结果。
- PDF / DOCX 真导出已可用，但正式导出仍是段落型。
- 当前导出返回的仍是服务器本地文件路径，不是真正的下载链接。
- 导出目录中已存在历史 `.html` / `.md` 与当前 `.pdf` / `.docx` 混存情况。

### 当前核心数据状态

| 表名 | 当前状态 |
| --- | --- |
| `students` | 当前 PostgreSQL 实查为 1 条 |
| `scores` | 当前 PostgreSQL 实查为 1 条 |
| `institutions` | 当前 PostgreSQL 实查为 0 条 |
| `majors` | 当前 PostgreSQL 实查为 0 条 |
| `province_batches` | 当前 PostgreSQL 实查为 0 条 |
| `admission_plans` | 当前 PostgreSQL 实查为 0 条 |
| `institution_admission_scores` | 当前 PostgreSQL 实查为 0 条 |
| `major_admission_scores` | 当前 PostgreSQL 实查为 0 条 |
| `subject_requirements` | 当前 PostgreSQL 实查为 0 条 |
| `institution_rules` | 当前未在本轮逐表核数，但需与正式导入状态一并复核 |
| `admission_risk_rules` | 当前 PostgreSQL 实查为 0 条 |
| `policy_trends` | 当前 PostgreSQL 实查为 0 条 |

### 当前真实风险

1. 当前 PostgreSQL 真实招生核心表为空，系统无法稳定给出真实招生推荐。
2. 前端还没有清楚标识“真实结果 / fallback 结果”，容易误导使用者。
3. 导出层还没有完成结构化交付，当前 PDF / DOCX 仍以段落为主。
4. 导出测试仍未完全拆分，仍保留一条 `planning_repository.export_report_package(...)` 集成链路。
5. 当前导出返回本地路径，不是真正可下载的文件链接。
6. 仓库里仍有 `backend/*.db` 级别的本地 SQLite 痕迹，和“统一 PostgreSQL”表述并不完全一致。
7. `data_assets/generated_reports/` 当前没有在 `.gitignore` 中统一忽略，且历史产物格式混杂，需要明确管理策略。
8. demo / base-data / settings 等页面仍在代码中存在，只是主导航弱化了入口。
9. 产品文档常写 `99 / 399 / 699 / 999`，但当前代码正式产品配置只有 `99 / 399 / 999`，存在口径偏差。

### 不在本轮处理范围内

- 不重构推荐算法
- 不继续跑全量 `python -m unittest discover -s backend/tests`
- 不继续生成新的 PDF / DOCX 产物
- 不做大规模前端重构
- 不在本轮直接扩省到多省正式可售
