# policy_trends 扩充执行记录

执行日期：`2026-06-13`

## 1. 本次目标

- 扩充河南当前正式库中的 `policy_trends`
- 补齐当前政策目录里遗漏的正式政策文件
- 把原本偏“原文截断”的趋势摘要改成可直接展示给学生和家长的正式摘要

## 2. 本次做了什么

### 2.1 新增漏接的对口招生问答文件

在 [backend/policy_importer.py](D:/2026workspace/Volunteer%20Application%20System/backend/policy_importer.py) 中新增接入：

- `河南省2026年普通高等学校对口招收中等职业学校毕业生工作相关事宜问答.docx`

新增 `policy_key`：

- `henan_2026_counterpart_faq`

该政策趋势重点覆盖：

- 对口招生报名对象
- 网上采集与现场确认
- 资格条件申报
- 本科 / 专科平行志愿数量
- 体检、专业考试与录取安排

### 2.2 为关键政策趋势补齐正式摘要

为以下政策补充 `summary_statements`，优先生成稳定、可读的正式摘要，而不是继续使用原文碎片硬截断：

- `henan_2026_general_regulation`
- `henan_2025_special_plan`
- `henan_2025_high_level_sports`
- `henan_2026_registration_faq`
- `henan_2026_sports_exam`
- `henan_2026_arts_exam`
- `henan_2025_single_exam`
- `henan_2026_counterpart_work`
- `henan_2026_counterpart_faq`

这一步的直接效果是：

- `general_regulation` 不再出现“以下简”这类截断噪音
- `single_exam`、`counterpart_work`、`registration_faq` 等政策摘要改成了可直接用于报告高亮的正式表述

### 2.3 补齐对口政策高亮命中能力

在 [backend/planning_repository.py](D:/2026workspace/Volunteer%20Application%20System/backend/planning_repository.py) 中扩充了 `STRICT_POLICY_SIGNAL_MAP`，新增：

- `registration`
- `single_exam`
- `counterpart`

这样推荐 / 报告链路在出现 `对口招生`、`中职`、`专业对照`、`高职单招` 等信号时，能更稳定地命中对应 `policy_trends`，而不是只依赖已有风险规则反推。

### 2.4 修复政策摘要清洗的边界问题

同步调整了 [backend/planning_repository.py](D:/2026workspace/Volunteer%20Application%20System/backend/planning_repository.py) 中的 `_clean_policy_summary`：

- 过滤纯章节标题
- 过滤含 `以下简` 的截断碎片

避免有价值的后置提醒句被前面两段噪音挤掉。

## 3. 测试与导入结果

### 3.1 单测结果

执行：

```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_policy_importer backend.tests.test_policy_highlights
```

结果：

- `Ran 13 tests ... OK`

### 3.2 dry-run 结果

执行：

```powershell
.\.venv\Scripts\python.exe backend/scripts/import_henan_policy_rules.py --dry-run
```

结果：

- `policy_trends: normalized=13`
- `admission_risk_rules: normalized=24`
- `institution_rules: normalized=76`

### 3.3 PostgreSQL 实际入库结果

正式导入后，当前 PostgreSQL 实查：

- `policy_trends = 13`
- `distinct policy_key = 13`

本次重点核验的正式摘要已入库：

- `henan_2026_general_regulation`
- `henan_2025_single_exam`
- `henan_2026_counterpart_work`
- `henan_2026_counterpart_faq`

## 4. 本次执行的命令

```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_policy_importer backend.tests.test_policy_highlights
.\.venv\Scripts\python.exe backend/scripts/import_henan_policy_rules.py --dry-run
.\.venv\Scripts\python.exe backend/scripts/import_henan_policy_rules.py
@'
from backend.database import db_session
with db_session() as conn:
    total = conn.execute("SELECT COUNT(*) AS total FROM policy_trends").fetchone()["total"]
    distinct_total = conn.execute("SELECT COUNT(DISTINCT policy_key) AS total FROM policy_trends").fetchone()["total"]
    print(total, distinct_total)
'@ | .\.venv\Scripts\python.exe -
```

## 5. 当前结论

这一步已经把 `policy_trends` 从“只有 12 条、且部分摘要仍是原文截断”，推进到“13 条、补齐对口问答、关键摘要可直接展示”的状态。

可以明确确认的结果是：

- 新增了 `henan_2026_counterpart_faq`
- `policy_trends` 总数从 `12` 增加到 `13`
- 关键政策摘要已改成正式可展示文案
- 对口 / 报名 / 单招类政策高亮命中能力得到补强

## 6. 剩余问题

- 部分 2025 特殊类型政策摘要虽然已经可用，但仍偏长，后续还可继续压缩成更统一的顾问展示口径
- 下一步应按清单进入 `province_batches` 补齐后的批次判断逻辑校验
