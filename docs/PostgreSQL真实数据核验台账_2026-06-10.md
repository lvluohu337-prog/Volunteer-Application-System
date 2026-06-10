# PostgreSQL 真实数据核验台账

核验日期：`2026-06-10`

核验目标：

- 确认当前运行时后端实际连接的 PostgreSQL 是否已具备真实招生数据。
- 区分“历史导入产物已准备好”与“当前 PostgreSQL 已实际落库”。
- 为后续 `P0` 数据恢复提供一份可引用的书面台账。

---

## 1. 本次核验范围

核验文件：

- `backend/database.py`
- `.env`
- `backend/scripts/*.py`
- `data_assets/imported/*.json`
- `TASKS_updated_with_staged_tasks.md`

核验命令：

```powershell
@'
from backend.database import db_session, get_postgres_conninfo
print('postgres_configured', 'yes' if get_postgres_conninfo() else 'no')
tables = [
    'students','scores','score_records','major_categories','city_industries','sample_students','report_template_fields',
    'institutions','majors','province_batches','score_segments','admission_plans','institution_admission_scores',
    'major_admission_scores','subject_requirements','institution_rules','admission_risk_rules','policy_trends',
    'report_advisor_notes','report_generation_records','report_delivery_records'
]
with db_session() as conn:
    for table in tables:
        total = conn.execute(f'SELECT COUNT(*) AS total FROM {table}').fetchone()['total']
        print(f'{table}\t{total}')
'@ | .\.venv\Scripts\python.exe -
```

```powershell
@'
from backend.database import db_session
queries = {
    'students_by_province': "SELECT COALESCE(province, '(null)') AS province, COUNT(*) AS total FROM students GROUP BY province ORDER BY total DESC",
    'score_segments_by_province': "SELECT COALESCE(province, '(null)') AS province, COUNT(*) AS total FROM score_segments GROUP BY province ORDER BY total DESC",
    'admission_plans_by_province': "SELECT COALESCE(province, '(null)') AS province, COUNT(*) AS total FROM admission_plans GROUP BY province ORDER BY total DESC",
    'major_scores_by_province': "SELECT COALESCE(province, '(null)') AS province, COUNT(*) AS total FROM major_admission_scores GROUP BY province ORDER BY total DESC",
    'institution_scores_by_province': "SELECT COALESCE(province, '(null)') AS province, COUNT(*) AS total FROM institution_admission_scores GROUP BY province ORDER BY total DESC",
    'subject_requirements_by_province': "SELECT COALESCE(province, '(null)') AS province, COUNT(*) AS total FROM subject_requirements GROUP BY province ORDER BY total DESC",
    'policy_trends_by_province': "SELECT COALESCE(province, '(null)') AS province, COUNT(*) AS total FROM policy_trends GROUP BY province ORDER BY total DESC",
    'risk_rules_by_province': "SELECT COALESCE(province, '(null)') AS province, COUNT(*) AS total FROM admission_risk_rules GROUP BY province ORDER BY total DESC"
}
with db_session() as conn:
    for name, sql in queries.items():
        print('---', name, '---')
        rows = conn.execute(sql).fetchall()
        if not rows:
            print('(empty)')
            continue
        for row in rows[:10]:
            print(f"{row['province']}\t{row['total']}")
'@ | .\.venv\Scripts\python.exe -
```

---

## 2. 核验结论

### 2.1 结论摘要

当前运行时 PostgreSQL 已正确配置并可连接，但真实招生核心表基本为空。

可以明确区分为两件事：

1. 当前代码和数据资产目录中，存在历史导入产物与导入摘要。
2. 当前后端实际连接的 PostgreSQL 中，这些数据并没有真正落库。

因此，当前系统的真实状态不是“数据部分缺失”，而是：

`当前运行时 PostgreSQL 基本没有真实招生数据，系统无法稳定命中真实招生候选。`

### 2.2 当前 PostgreSQL 实查结果

| 表名 | 当前行数 | 说明 |
| --- | ---: | --- |
| `students` | 1 | 有 1 条学生数据 |
| `scores` | 1 | 有 1 条成绩快照 |
| `score_records` | 0 | 暂无历史成绩记录 |
| `major_categories` | 0 | 基础方向库未落库 |
| `city_industries` | 0 | 城市产业库未落库 |
| `sample_students` | 0 | 样例学生未落库 |
| `report_template_fields` | 0 | 报告模板字段未落库 |
| `institutions` | 0 | 真实院校表为空 |
| `majors` | 0 | 真实专业表为空 |
| `province_batches` | 0 | 批次表为空 |
| `score_segments` | 0 | 一分一段表为空 |
| `admission_plans` | 0 | 招生计划表为空 |
| `institution_admission_scores` | 0 | 院校录取分表为空 |
| `major_admission_scores` | 0 | 专业录取分表为空 |
| `subject_requirements` | 0 | 选科要求表为空 |
| `institution_rules` | 0 | 院校规则表为空 |
| `admission_risk_rules` | 0 | 风险规则表为空 |
| `policy_trends` | 0 | 政策趋势表为空 |
| `report_advisor_notes` | 0 | 暂无顾问备注 |
| `report_generation_records` | 1 | 有 1 条报告生成留痕 |
| `report_delivery_records` | 0 | 暂无导出留痕 |

### 2.3 当前省份分布

- `students`：仅 `河南 = 1`
- `score_segments`：空
- `admission_plans`：空
- `major_admission_scores`：空
- `institution_admission_scores`：空
- `subject_requirements`：空
- `policy_trends`：空
- `admission_risk_rules`：空

---

## 3. 与本地导入产物的对照结果

### 3.1 `data_assets/imported` 中存在历史导入摘要

本地目录中已经存在这些导入产物摘要：

- `data_assets/imported/import_summary.json`
- `data_assets/imported/henan_province_batches/henan_province_batches_import_summary.json`
- `data_assets/imported/henan_score_segments/henan_score_segments_import_summary.json`
- `data_assets/imported/henan_subject_requirements/henan_subject_requirements_import_summary.json`
- 以及 `henan_admission_plans` / `henan_institution_admission_scores` / `henan_major_admission_scores` / `henan_institution_rules` 等目录

### 3.2 历史导入摘要显示“曾经准备好数据”

从这些摘要文件可见，历史上至少整理过以下规模的数据：

- `major_categories = 14`
- `city_industries = 12`
- `sample_students = 12`
- `report_template_fields = 11`
- `province_batches = 142`
- `score_segments = 12111`
- `subject_requirements = 60449`
- 历史摘要中还出现过：
  - `institutions ≈ 5731 / 5738`
  - `majors ≈ 58367 / 99775`
  - `admission_plans ≈ 442882`
  - `institution_admission_scores ≈ 16278 / 35298`
  - `major_admission_scores ≈ 130679 / 304053`
  - `institution_rules ≈ 133 / 5516`
  - `admission_risk_rules = 14`
  - `policy_trends = 9`

### 3.3 关键差异

历史导入摘要不等于当前运行时 PostgreSQL 已落库。

当前可确认的事实是：

- `data_assets/imported` 里有“曾经整理过、曾经导入过、或曾经生成过导入摘要”的痕迹。
- 当前后端连接的 PostgreSQL 库里，这些表实际仍是空的。

换句话说：

`当前问题不是“没有准备数据”，而是“当前服务连接的数据库没有拿到这些数据”。`

---

## 4. 当前系统影响

### 4.1 对推荐链路的影响

由于真实招生核心表为空，以下能力无法稳定成立：

- 基于真实院校/专业数据筛选候选
- 基于批次、一分一段、历年分数线进行真实匹配
- 基于选科要求过滤不符合条件的候选
- 基于真实计划和风险规则输出正式建议

### 4.2 对页面和报告的影响

前端虽然已经具备这些展示结构：

- `recommendationTable`
- `firstChoice`
- `alternatives`
- `notRecommended`

但在当前数据库状态下，这些结果大概率来自 fallback 或画像/规则兜底，而不是当前数据库中的真实招生数据。

### 4.3 对文档和认知的影响

当前仓库里同时存在两种信息：

1. 历史导入摘要显示“数据准备过”。
2. 当前运行时 PostgreSQL 实查显示“数据没有在当前库里”。

如果不把这两件事分开，后续会持续出现误判：

- 误以为“系统已经有真实数据，只是页面没接好”
- 误以为“报告逻辑有问题”，但真正的问题是“当前库是空的”

---

## 5. 当前最可能的原因

结合目录和摘要信息，当前最可能存在以下情况之一或同时存在：

1. 历史导入是在另一套 PostgreSQL 实例中完成的，当前 `.env` 指向了不同库。
2. 历史导入只生成了 `data_assets/imported` 的中间产物或摘要，没有真正写入当前库。
3. 当前库曾被重建、清空或切换过。
4. 基础数据导入脚本没有在当前环境重新执行。

当前台账只确认现状，不直接认定具体原因，需要在下一步导入核验中继续确认。

---

## 6. 下一步建议

### 6.1 直接优先执行的脚本

建议先从这些脚本开始核验和重导：

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

### 6.2 每跑完一类导入后的复核命令

```powershell
@'
from backend.database import db_session
tables = [
    "major_categories","city_industries","sample_students","report_template_fields",
    "institutions","majors","province_batches","score_segments","admission_plans",
    "institution_admission_scores","major_admission_scores","subject_requirements",
    "institution_rules","admission_risk_rules","policy_trends"
]
with db_session() as conn:
    for table in tables:
        total = conn.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()["total"]
        print(table, total)
'@ | .\.venv\Scripts\python.exe -
```

### 6.3 下一项任务衔接

本台账完成后，下一步应进入：

- `P0 / 补齐 institutions`
- `P0 / 补齐 majors`
- `P0 / 补齐 admission_plans`
- `P0 / 补齐 institution_admission_scores`
- `P0 / 补齐 major_admission_scores`
- `P0 / 补齐 subject_requirements`
- `P0 / 补齐 province_batches`
- `P0 / 补齐 admission_risk_rules`
- `P0 / 补齐 policy_trends`

---

## 7. 本项任务完成判定

`P0 第 1 项：核验当前 PostgreSQL 连接的真实数据状态，并形成书面台账`

完成情况：

- [x] 已确认 PostgreSQL 连接有效
- [x] 已逐表核验当前运行时 PostgreSQL 行数
- [x] 已确认省份分布现状
- [x] 已对照 `data_assets/imported` 历史导入摘要
- [x] 已形成独立书面台账

结论：

`该任务已完成，可在 TASKS 中勾选。`
