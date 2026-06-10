# PostgreSQL 真实数据导入执行记录

执行日期：`2026-06-10`

## 1. 本次目标

- 从 `import_foundation_data.py` 和河南相关导入脚本开始，把当前项目目录中的可用真实数据真正导入当前 PostgreSQL。
- 在导入前先区分 `data_assets/imported`、`data-needed-standardized`、`河南-2026志愿填报资料` 各自的角色，避免把历史产物误当成权威源。
- 导入后用 PostgreSQL 实际行数回查，而不是只看脚本输出。

## 2. 先确认的数据目录角色

### `data_assets/imported`

这不是本次导入的主数据源，而是各导入脚本运行后生成的“中间产物/留痕目录”，主要包括：

- `*.sample.json` / `*.sample.csv`
- `*_import_summary.json`
- 基础数据包提取后的 `major_categories.json`、`city_industries.json` 等

它的价值是：

- 方便抽查脚本清洗结果
- 保留上一次运行的样例和摘要
- 帮助追踪导入规模

它的局限是：

- 不能证明当前 PostgreSQL 已经有数据
- 目录结构并不完全统一
- 里面的历史摘要可能来自旧环境、旧数据库或仅样例生成阶段

### `data_assets/data-needed-standardized`

这是整理后的标准化数据工作目录，适合作为正式导入前的候选源目录。`README.md` 和目录结构都表明它是“后续清洗、字段映射、导入”的推荐工作区。

本次实际使用到的子目录包括：

- `00_foundation` 的基础包并未直接走这里，而是走 `data_assets/raw`
- `02_batches_policies`：河南批次线
- `05_admission_plans`：河南招生计划
- `06_policy_rules`：院校章程规则表

### `河南-2026志愿填报资料`

这是多张河南真实招生数据表的直接原始来源。本次实际使用到：

- 一分一段
- 选科要求
- 院校投档线
- 专业分数线
- 政策文档

## 3. 导入前发现并修复的问题

### 3.1 脚本直接执行时找不到 `backend` 包

受影响脚本：

- `backend/scripts/import_foundation_data.py`
- `backend/scripts/import_henan_policy_rules.py`

处理方式：

- 增加与其他脚本一致的 `sys.path` 兜底逻辑，使它们可以从项目根目录直接运行。

### 3.2 `import_admission_plans.py` 依赖旧机器的绝对路径

现象：

- `05_admission_plans_inventory.csv` 中保存的是旧路径前缀，例如 `D:\志愿填报系统\...`
- 在当前工作区执行时，脚本会因为找不到文件而中断

处理方式：

- 在 `backend/scripts/import_admission_plans.py` 中新增运行时路径重定位逻辑
- 优先使用清单原路径
- 原路径不存在时，自动把 `data_assets\...` 或 `data-needed-standardized\...` 之后的相对段重映射到当前项目根目录

这样做的好处是：

- 不改动原始清单文件
- 不破坏后续追溯
- 当前项目可以直接复用历史整理成果

## 4. 本次执行的脚本

### 4.1 先做的 dry-run

```powershell
.\.venv\Scripts\python.exe backend/scripts/import_province_batches.py --dry-run
.\.venv\Scripts\python.exe backend/scripts/import_score_segments.py --dry-run
.\.venv\Scripts\python.exe backend/scripts/import_subject_requirements.py --dry-run
.\.venv\Scripts\python.exe backend/scripts/import_admission_plans.py --dry-run
.\.venv\Scripts\python.exe backend/scripts/import_institution_admission_scores.py --dry-run
.\.venv\Scripts\python.exe backend/scripts/import_major_admission_scores.py --dry-run
.\.venv\Scripts\python.exe backend/scripts/import_institution_rules.py --dry-run
.\.venv\Scripts\python.exe backend/scripts/import_henan_policy_rules.py --dry-run
```

dry-run 结论：

- `province_batches`：`142`
- `score_segments`：`12111`
- `subject_requirements`：`60449`
- `admission_plans`：`412313`
- `institution_admission_scores`：`21690`
- `major_admission_scores`：`178139`
- `institution_rules`：`6214`
- `policy_trends`：`9`
- `admission_risk_rules`：`14`

### 4.2 实际落库顺序

```powershell
.\.venv\Scripts\python.exe backend/scripts/import_foundation_data.py
.\.venv\Scripts\python.exe backend/scripts/import_province_batches.py
.\.venv\Scripts\python.exe backend/scripts/import_score_segments.py
.\.venv\Scripts\python.exe backend/scripts/import_subject_requirements.py
.\.venv\Scripts\python.exe backend/scripts/import_admission_plans.py
.\.venv\Scripts\python.exe backend/scripts/import_institution_admission_scores.py
.\.venv\Scripts\python.exe backend/scripts/import_major_admission_scores.py
.\.venv\Scripts\python.exe backend/scripts/import_institution_rules.py
.\.venv\Scripts\python.exe backend/scripts/import_henan_policy_rules.py
```

## 5. 实际完成情况

### 5.1 PostgreSQL 基线

导入前，以下目标表均为 `0` 行：

- `major_categories`
- `city_industries`
- `sample_students`
- `report_template_fields`
- `institutions`
- `majors`
- `province_batches`
- `score_segments`
- `subject_requirements`
- `admission_plans`
- `institution_admission_scores`
- `major_admission_scores`
- `institution_rules`
- `admission_risk_rules`
- `policy_trends`

### 5.2 导入后的实际表行数

| 表名 | 最终行数 |
| --- | ---: |
| `major_categories` | 14 |
| `city_industries` | 12 |
| `sample_students` | 12 |
| `report_template_fields` | 11 |
| `institutions` | 5738 |
| `majors` | 99775 |
| `province_batches` | 142 |
| `score_segments` | 12111 |
| `subject_requirements` | 60449 |
| `admission_plans` | 300696 |
| `institution_admission_scores` | 19020 |
| `major_admission_scores` | 173374 |
| `institution_rules` | 5478 |
| `admission_risk_rules` | 14 |
| `policy_trends` | 9 |

### 5.3 年份覆盖核验

#### `province_batches`

- `2008` 到 `2022`

#### `score_segments`

- `2017` 到 `2025`

#### `subject_requirements`

- `2025`

#### `admission_plans`

- `2017` 到 `2024`

#### `institution_admission_scores`

- `2017` 到 `2021`

#### `major_admission_scores`

- `2017` 到 `2021`

#### `institution_rules`

- `NULL` 年份：`5402`
- `2025`：`76`

说明：

- `NULL` 年份主要来自章程规则表本身未明确给出年份字段
- `2025` 的 `76` 条来自河南政策文档抽取脚本

#### `policy_trends`

- `2025`：`6`
- `2026`：`3`

## 6. 需要注意的差异

### 6.1 “normalized / upserted” 不等于最终表总数

例如：

- `admission_plans` dry-run 规范化记录数是 `412313`，最终表总数是 `300696`
- `institution_admission_scores` 规范化记录数是 `21690`，最终表总数是 `19020`
- `major_admission_scores` 规范化记录数是 `178139`，最终表总数是 `173374`

这通常意味着：

- 导入过程中存在按业务主键去重
- 多来源或多年份文件之间有重复记录被 upsert 覆盖
- “脚本处理过多少条” 和 “表里最终保留多少唯一记录” 不是同一个指标

### 6.2 `imported` 目录现在可以当作留痕，但仍不能当权威事实来源

本次真实导入完成后，`data_assets/imported` 中的摘要文件已经更接近当前库状态，但它仍然只是导入副产物。最终是否成功，仍应以 PostgreSQL 实查结果为准。

## 7. 本次修改的代码文件

- `backend/scripts/import_foundation_data.py`
- `backend/scripts/import_admission_plans.py`
- `backend/scripts/import_henan_policy_rules.py`

改动性质：

- 都是“让现有导入脚本能在当前工作区稳定执行”的工程性修复
- 没有改业务表结构
- 没有改原始源数据文件

## 8. 与任务清单的同步

已同步更新 `TASKS_updated_with_staged_tasks.md` 中 `P0 / 真实招生数据链路` 的这些项：

- `institutions`
- `majors`
- `admission_plans`
- `institution_admission_scores`
- `major_admission_scores`
- `subject_requirements`
- `province_batches`
- `institution_rules`
- `admission_risk_rules`
- `policy_trends`

## 9. 当前结论

本次任务已经把“当前 PostgreSQL 几乎没有真实招生核心数据”的状态，推进为“河南真实招生主链已实际落库并可按表核验”的状态。

仍然没有在本次任务里完成的，是下一步的能力验证：

- `backend/planning_repository.py` 是否已经稳定命中这些真实表
- 前端/报告链路是否还会落回 fallback
- 其它省份是否具备与河南同等级别的真实数据覆盖
