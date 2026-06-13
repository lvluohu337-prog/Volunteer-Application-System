# TASKS

## 使用规则

这份文档只保留一套可持续维护的结构：

1. `当前执行清单`
   这是唯一需要持续勾选状态的地方，也是当前迭代的唯一进度源。
2. `产品定义`
   说明 99 / 399 / 999 当前已落地档位，以及 699 深度档位目标边界，不在这里重复维护开发状态。
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

当前系统已经不只是“录入页 + 报告页”的演示壳，而是已经具备了一条可运行的正式主流程：

- 主导航已收敛到 `dashboard / students / intake / reports`，分析、专业、方案页由学生工作台按步骤进入。
- 学生工作台已经承接“录入 -> 画像 -> 专业 -> 方案 -> 报告 -> 导出”的流程引导。
- `shared/province_support.json` 已成为正式支持省份的单一来源，当前正式支持范围明确为 `河南`。
- `shared/report_products.json` 已成为产品档位单一来源，当前正式支持档位明确为 `99 / 399 / 999`，`699` 仅为 planned。
- `Intake / Analysis / Majors / Plan / Reports` 五个主链路页面都已补上显式失败态，不再在接口失败时静默展示假数据。
- 报告链路已具备结构化推荐表、导出留痕、正式下载接口和前端直接下载能力。
- 河南真实库当前实查已达到：`institutions 5738`、`majors 99775`、`admission_plans 300696`、`institution_admission_scores 19020`、`major_admission_scores 173374`、`subject_requirements 60449`、`score_segments 12111`、`province_batches 142`、`institution_rules 10115`、`admission_risk_rules 24`、`policy_trends 13`。

当前最需要收口的重点，已经从“先把数据导进去”转成了“把正式边界、系统级配置、解释层内容和文档口径同步收稳”。

当前最大的 6 个缺口：

1. 系统级配置还没有正式落地入口，顾问署名、导出签名、合规文案等仍有页面级硬编码。
2. 当前正式支持省份仍只有 `河南`；浙江、河北、山东、江苏、安徽、广东、四川仅处于“已核验待接入”。
3. 主链路页面失败态已补齐，但 `DashboardPage.vue`、`StudentDetailPage.vue`、`BaseDataPage.vue` 仍缺统一的失败恢复体验。
4. 本地专业解释库、城市解释库、画像映射库和报告话术库还未系统化，399 档解释层价值仍偏弱。
5. 仓库文档口径还没有完全同步，`README.md` 和部分历史 docs 仍保留旧数据量、旧页面引用和旧阶段描述。
6. `699` 深度版能力仍未产品化，多方案对比、考研路径、就业迁移和人工复核入口都还未落地。

---

## 当前执行清单

### 已完成

#### 产品流程

- [x] 将学生详情页改造成核心业务入口
- [x] 在学生详情页展示当前流程进度
- [x] 每一步显示“下一步操作”提示
- [x] 工作台快捷入口只保留核心流程
- [x] 弱化主导航中的演示型入口

#### 正式支持边界收口

- [x] 将正式支持省份定义收口到 `shared/province_support.json`
- [x] 录入页只允许正式支持省份新建正式学生档案
- [x] 将正式产品档位定义收口到 `shared/report_products.json`
- [x] 统一当前正式口径为 `99 / 399 / 999`，并将 `699` 标记为 `planned`

#### 推荐结果接入

- [x] `backend/admissions_engine.py` 产出结构化推荐结果
- [x] `backend/planning_repository.py` 将结构化推荐结果接入正式报告 JSON
- [x] `src/pages/ReportsPage.vue` 展示院校专业推荐表、第一志愿、备选志愿、不建议项

#### 导出基础链路

- [x] `backend/report_exporters.py` 能生成真实 `.pdf` 文件
- [x] `backend/report_exporters.py` 能生成真实 `.docx` 文件
- [x] `backend/planning_repository.py` 已接好正式导出产物落盘与留痕
- [x] `backend/main.py` 已提供 PDF / Word 导出 API

#### 下载链路

- [x] 增加正式下载接口，而不是只返回服务器本地文件路径
- [x] 前端点击“导出 PDF / Word”后可直接下载文件
- [x] 导出记录页优先展示可访问的下载入口，而不只是磁盘路径
- [x] 已为下载路由补上最小回归测试

#### 前端失败态与风险提示

- [x] 新增 `src/components/RequestErrorNotice.vue`
- [x] `src/pages/IntakePage.vue` 在模板或详情接口失败时显示显式错误卡
- [x] `src/pages/AnalysisPage.vue` 在分析接口失败时显示显式错误卡
- [x] `src/pages/MajorsPage.vue` 在专业推荐接口失败时显示显式错误卡
- [x] `src/pages/PlanPage.vue` 在方案接口失败时显示显式错误卡
- [x] `src/pages/ReportsPage.vue` 在报告接口失败时显示显式错误卡
- [x] 画像推导失败时不再静默切回示例画像
- [x] 建立 `scripts/test_frontend_error_states.ps1` 与 `scripts/check_frontend_error_states.cjs` 作为失败态回归脚本

#### 数据底座

- [x] PostgreSQL 已成为唯一运行时数据库入口
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
- [x] DOCX 中展示清晰的冲 / 稳 / 保推荐表
- [x] 导出中展示专业组/代码、最低分、最低位次、位次差、风险等级、推荐理由
- [x] 导出中补齐调剂风险、选科限制、计划变化风险、热门专业风险提示
- [x] 导出中补齐第一志愿、备选志愿、不建议报考项

#### 测试稳定性

- [x] 将导出测试拆成“纯 exporter 单测”和“最小集成测试”
- [x] 移除 exporter 单测对 `planning_repository` 的直接依赖
- [x] 导出单测统一使用最小 mock `report_data`
- [x] 单个测试文件命令统一加超时约束，确保不会长时间卡住
- [x] 建立导出链路最小回归测试
- [x] 建立结果来源与下载链路测试
- [x] 建立 `province_batches` 批次判断逻辑测试

#### 合规边界

- [x] 统一报告页、导出报告、顾问话术中的免责声明
- [x] 检查是否存在容易被理解为“保录”“必中”的表述
- [x] 保持画像层只用于解释，不覆盖真实录取判断

### P1

#### 数据层补强

- [x] 明确当前“正式支持省份”清单
- [x] 核验浙江等目标省份是否已有与河南同等级别的真实招生数据
- [x] 扩充 `admission_risk_rules`
- [x] 扩充 `institution_rules`
- [x] 扩充 `policy_trends`
- [x] 补齐 `province_batches` 后校验批次判断逻辑
- [x] 建立真实数据导入后的最小验收脚本

#### 前端稳定性

- [ ] 清理关键链路中的静默 mock 回退
- [ ] 明确哪些前端空态属于“无学生/无结果”，哪些场景必须真实报错
- [ ] 为 `src/pages/DashboardPage.vue`、`src/pages/StudentDetailPage.vue`、`src/pages/BaseDataPage.vue` 增加统一失败态和重试入口
- [ ] 把“接口失败”和“暂无正式结果”在更多页面上彻底分离

#### 系统级配置最小可用化

- [ ] 为顾问署名、导出签名、合规文案建立统一配置来源，不再只在页面中硬编码
- [ ] 为产品版本展示、正式支持省份说明和顾问信息补齐统一读取层
- [ ] 评估是否需要独立“系统配置页”；如果没有明确收益，则保持“共享配置 + 最小接口”方案
- [ ] 保持配置能力只覆盖正式交付必需项，不扩成大而全后台

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

- [ ] 同步 `README.md` 中的数据库计数、阶段结论和页面入口描述
- [ ] 梳理历史 docs 中仍保留的旧计数和旧阶段结论，避免和当前台账冲突
- [ ] 清理仓库中的 SQLite 痕迹与“已统一 PostgreSQL”不一致的说明
- [ ] 明确 `BaseDataPage.vue` 的长期定位，避免被误认成正式主流程页面
- [ ] 统一 `99 / 399 / 999 / 699` 的产品口径，避免文档与代码再次错位

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

1. 收口前端剩余失败态与空态边界
2. 收口系统级共享配置，去掉顾问与导出信息的页面级硬编码
3. 建设本地专业 / 城市 / 画像 / 话术解释库
4. 同步 README 与历史 docs 的真实数据计数和阶段口径
5. 推进多省从“已核验待接入”走向正式导入闭环
6. 打开 699 / 999 深度版能力

---

## 产品定义

### 当前代码已落地档位

- `99`：基础版报告
- `399`：标准版报告
- `999`：人工咨询版报告

说明：

- 当前正式产品定义已收口到共享配置 `shared/report_products.json`，前后端和测试都应以它为准。
- 当前正式支持档位只有 `99 / 399 / 999`。
- `699` 目前明确归类为“规划中能力”，不属于当前正式交付口径，也不会在系统里作为正式版本对外提供。

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

### 699 元深度版（规划中）

定位：

- 深度咨询扩展版，当前暂不正式交付

应包含：

- 399 元全部内容
- 名校优先 / 专业优先 / 城市优先三套方案
- 考研路径分析
- 就业路径和城市迁移路径
- 家庭预算 / 距离 / 是否出省等约束条件建议
- 顾问人工复核建议

### 999 元人工咨询版

定位：

- 当前正式支持的高配人工咨询交付版

应包含：

- 399 元全部内容
- 咨询师补充备注
- 家长沟通脚本 / 复核记录
- 多轮调整与正式交付留痕

---

## 阶段路线图

### 阶段 1：项目盘点

目标：

- 识别真实业务页面与辅助页面
- 确认真实推荐逻辑、报告逻辑、导出逻辑所在文件
- 核验真实数据是否真的已入库

已产出：

- `docs/志愿报告功能差距分析.md`
- `docs/系统目标差距分析.md`
- `docs/目标省份真实数据覆盖核验_2026-06-12.md`
- `docs/institution_rules扩充执行记录_2026-06-13.md`
- `docs/policy_trends扩充执行记录_2026-06-13.md`
- `docs/province_batches批次判断逻辑校验执行记录_2026-06-13.md`

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
- 明确哪些页面属于主流程，哪些页面属于辅助查看页。

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
    "students","scores","score_records","institutions","majors","province_batches",
    "score_segments","admission_plans","institution_admission_scores","major_admission_scores",
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
- `src/router/index.js`
命令：
```powershell
Get-Content src/App.vue -Encoding utf8
Get-Content src/router/index.js -Encoding utf8
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

4. 复核辅助页面是否已降级为非主流程  
文件：
- `src/pages/BaseDataPage.vue`
- `src/router/index.js`
命令：
```powershell
Get-Content src/pages/BaseDataPage.vue -Encoding utf8
rg -n "base-data" src/router/index.js
```
验收：
- 辅助页面不再占据主流程入口，且其定位说明清楚。

### 阶段 3：打通结构化推荐结果

目标：

- 后端产出正式推荐结果
- 报告页展示正式推荐结果

当前状态：

- 已完成

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

2. 增加“真实结果 / fallback 结果”标识  
文件：
- `backend/planning_repository.py`
- `src/pages/AnalysisPage.vue`
- `src/pages/MajorsPage.vue`
- `src/pages/PlanPage.vue`
- `src/pages/ReportsPage.vue`
命令：
```powershell
rg -n "resultSource|fallbackReason|matchedCandidateCount|candidateStrategy" src/pages backend/planning_repository.py
```
验收：
- 页面能明确显示当前结果来源和风险级别。

3. 回归验证结构化推荐输出  
文件：
- `backend/tests/test_admissions_engine.py`
- `backend/tests/test_planning_repository_structured_report.py`
- `backend/tests/test_planning_result_source.py`
命令：
```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_admissions_engine backend.tests.test_planning_repository_structured_report backend.tests.test_planning_result_source
```
验收：
- `recommendationTable`、`firstChoice`、`alternatives`、`notRecommended` 结构稳定。

### 阶段 4：完成正式导出

目标：

- PDF / DOCX 成为真正可交付的正式报告

当前状态：

- 已完成

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

3. 拆分导出测试与下载测试  
文件：
- `backend/tests/report_export_fixtures.py`
- `backend/tests/test_report_exporter_unit.py`
- `backend/tests/test_report_export_integration.py`
- `backend/tests/test_report_delivery_download.py`
- `backend/scripts/run_unittest_module.py`
命令：
```powershell
.\.venv\Scripts\python.exe backend\scripts\run_unittest_module.py backend.tests.test_report_exporter_unit --timeout-seconds 30
.\.venv\Scripts\python.exe backend\scripts\run_unittest_module.py backend.tests.test_report_export_integration --timeout-seconds 30
.\.venv\Scripts\python.exe -m unittest backend.tests.test_report_delivery_download
```
验收：
- 纯 exporter 单测不再直接依赖 `planning_repository`
- 导出链路和下载链路都有最小回归测试

### 阶段 5：补足正式边界与深度内容

目标：

- 收口正式支持范围
- 补强系统配置和解释层内容
- 打开 699 / 999 深度版能力

当前状态：

- 进行中

执行清单（文件 / 命令）：

1. 明确正式支持省份清单  
文件：
- `shared/province_support.json`
- `backend/province_support.py`
- `src/pages/IntakePage.vue`
命令：
```powershell
Get-Content shared/province_support.json -Encoding utf8
Get-Content backend/province_support.py -Encoding utf8
rg -n "province_support|formalSupportedProvinces|pendingProvinces" src/pages/IntakePage.vue backend
```
验收：
- 文档里明确列出“已正式支持 / 已核验待接入”的省份清单。

2. 补强风险、规则、政策覆盖  
文件：
- `backend/scripts/import_institution_rules.py`
- `backend/scripts/import_henan_policy_rules.py`
- `docs/institution_rules扩充执行记录_2026-06-13.md`
- `docs/policy_trends扩充执行记录_2026-06-13.md`
- `docs/province_batches批次判断逻辑校验执行记录_2026-06-13.md`
命令：
```powershell
.\.venv\Scripts\python.exe backend/scripts/import_institution_rules.py --dry-run
.\.venv\Scripts\python.exe backend/scripts/import_henan_policy_rules.py --dry-run
```
验收：
- `institution_rules`、`admission_risk_rules`、`policy_trends` 有稳定可用数据，并有可追溯执行记录。

3. 建设专业 / 城市 / 画像解释库  
文件：
- `backend/foundation_repository.py`
- `data_assets/`
- `src/pages/ReportsPage.vue`
命令：
```powershell
rg -n "major_categories|city_industries|report_template_fields|portraitRecommendation" backend data_assets src
```
验收：
- 报告里能区分“数据依据”和“解释依据”，并支撑 399 档交付深度。

4. 收口系统级共享配置  
文件：
- `shared/report_products.json`
- `shared/province_support.json`
- `src/pages/ReportsPage.vue`
- `src/pages/IntakePage.vue`
命令：
```powershell
rg -n "author_name|includeSignature|report_products|province_support" shared src backend
```
验收：
- 顾问信息、产品口径和省份边界不再分散硬编码。

5. 回归验证阶段成果  
文件：
- `backend/tests/*.py`
- `src/pages/*.vue`
- `scripts/test_frontend_error_states.ps1`
命令：
```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_admissions_engine backend.tests.test_admissions_engine_batch_logic backend.tests.test_planning_result_source backend.tests.test_report_exporter_unit backend.tests.test_report_export_integration backend.tests.test_report_delivery_download
npm run build
npm run test:frontend:error-states
```
验收：
- 后端核心测试通过，前端可构建，主链路失败态可回归验证。

---

## 项目台账

### 当前系统快照

- 主导航当前只保留 `dashboard / students / intake / reports`，其余页面改为由学生工作台按步骤进入。
- 学生工作台已承担正式主流程入口角色。
- `Intake / Analysis / Majors / Plan / Reports` 已补显式错误卡，接口失败时不再静默展示假结果。
- 报告接口已能返回结构化推荐结果与结果来源标识。
- PDF / DOCX 导出和导出后直接下载已打通，并会写入 `report_delivery_records`。
- 当前正式支持省份和产品档位都已收口到 `shared/` 共享定义。
- 基础数据查看页仍作为辅助查看页保留，但不是正式交付主流程的一部分。

### 当前核心数据状态

| 表名 | 当前状态 |
| --- | --- |
| `students` | 当前 PostgreSQL 实查为 `4` 条 |
| `scores` | 当前 PostgreSQL 实查为 `3` 条 |
| `score_records` | 当前 PostgreSQL 实查为 `0` 条 |
| `institutions` | 当前 PostgreSQL 实查为 `5738` 条 |
| `majors` | 当前 PostgreSQL 实查为 `99775` 条 |
| `admission_plans` | 当前 PostgreSQL 实查为 `300696` 条 |
| `institution_admission_scores` | 当前 PostgreSQL 实查为 `19020` 条 |
| `major_admission_scores` | 当前 PostgreSQL 实查为 `173374` 条 |
| `subject_requirements` | 当前 PostgreSQL 实查为 `60449` 条 |
| `score_segments` | 当前 PostgreSQL 实查为 `12111` 条 |
| `province_batches` | 当前 PostgreSQL 实查为 `142` 条，且已接入批次判断逻辑 |
| `institution_rules` | 当前 PostgreSQL 实查为 `10115` 条，已完成扩充并落入真实库 |
| `admission_risk_rules` | 当前 PostgreSQL 实查为 `24` 条 |
| `policy_trends` | 当前 PostgreSQL 实查为 `13` 条，已补入 `对口招生问答` 并更新正式摘要 |

### 当前正式支持省份状态

| 省份 | 状态 | 说明 |
| --- | --- | --- |
| `河南` | 正式支持 | 真实招生主链已完成导入并形成正式推荐与报告交付闭环 |
| `浙江` | 已核验待接入 | 已有标准化素材，但尚无正式导入闭环 |
| `河北` | 已核验待接入 | 已有标准化素材，但尚无正式导入闭环 |
| `山东` | 已核验待接入 | 已有标准化素材，但尚无正式导入闭环 |
| `江苏` | 已核验待接入 | 已有标准化素材，但尚无正式导入闭环 |
| `安徽` | 已核验待接入 | 已有标准化素材，但尚无正式导入闭环 |
| `广东` | 已核验待接入 | 已有标准化素材，但尚无正式导入闭环 |
| `四川` | 已核验待接入 | 已有标准化素材，但尚无正式导入闭环 |

### 当前真实风险

1. 当前正式支持省份边界已经明确为 `河南`；其它目标省份虽然已核验素材，但还没有形成与河南同等级别的正式导入闭环。
2. 主链路五个学生驱动页面已补显式错误态，但 `DashboardPage.vue`、`StudentDetailPage.vue`、`BaseDataPage.vue` 仍缺统一的失败恢复体验。
3. 报告页里仍存在顾问信息与导出行为的页面级硬编码，例如默认 `author_name = 张老师`、导出默认 `includeSignature = true`，系统级配置尚未收口。
4. 本地专业 / 城市 / 画像 / 话术解释库尚未建立，当前 399 元标准版的解释层说服力还有提升空间。
5. `README.md` 与部分历史 docs 仍保留旧数据量、旧页面引用和旧阶段结论，和当前仓库现状不完全一致。
6. 仓库中仍保留 `backend/gaokao_planning.db` 等 SQLite 历史痕迹，和“运行时仅支持 PostgreSQL”的口径不完全一致。
7. `BaseDataPage.vue` 仍然可通过路由直接访问，虽然不在主导航内，但长期定位还需要继续明确。
8. `699` 深度版能力仍停留在规划口径，尚未落地为正式可售能力。
9. `institution_rules` 虽已扩充入库，但当前标准化章程里仍有 `371` 个院校名未匹配到正式院校库，后续需要配合院校主数据补齐别名或清洗规则。

### 不在本轮处理范围内

- 不重构推荐算法
- 不继续跑全量 `python -m unittest discover -s backend/tests`
- 不继续生成新的 PDF / DOCX 产物
- 不做大规模前端重构
- 不在本轮直接扩省到多省正式可售
