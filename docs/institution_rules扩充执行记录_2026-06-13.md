# institution_rules 扩充执行记录

执行日期：`2026-06-13`

## 1. 本次目标

- 扩充河南当前正式库中的 `institution_rules`
- 把招生章程中的高价值约束从“零散原文”提升为可检索、可展示、可导出的结构化规则
- 保证 `backend/scripts/import_institution_rules.py` 在 `--dry-run` 场景下也能稳定运行，不依赖数据库在线

## 2. 本次做了什么

### 2.1 扩充规则类型识别

在 [backend/institution_rule_parser.py](D:/2026workspace/Volunteer%20Application%20System/backend/institution_rule_parser.py) 中新增了以下规则类型：

- `single_subject_requirement`
- `tuition_requirement`
- `campus_assignment`
- `pilot_class_pathway`
- `graduate_recommendation`
- `gender_requirement`

这次保留了原有的：

- `language_requirement`
- `physical_requirement`
- `adjustment_policy`
- `cooperative_education`
- `special_program`
- `subject_selection_reference`

这样招生章程里原本容易被漏掉的“学费、校区、实验班分流、保研通道、性别限制、单科门槛”等信息，也能进入正式规则表。

### 2.2 补齐通用政策主题映射

同步补齐了 `GENERAL_POLICY_TOPICS` 映射，确保新增规则类型在后续展示、报告引用和回溯政策主题时不会落成空主题。

### 2.3 修复 dry-run 依赖数据库的问题

调整了 [backend/scripts/import_institution_rules.py](D:/2026workspace/Volunteer%20Application%20System/backend/scripts/import_institution_rules.py)：

- `--dry-run` 时不再强制访问 PostgreSQL
- 摘要文件中新增 `coverageMode`
- dry-run 场景下写入 `coverageMode: "dry_run_without_db"`
- 正式导入场景下写入 `coverageMode: "db_validated"`

这样即使数据库未启动，也可以先完成章程解析、规则归一化和覆盖面预检查。

### 2.4 补齐解析单测

在 [backend/tests/test_institution_rule_parser.py](D:/2026workspace/Volunteer%20Application%20System/backend/tests/test_institution_rule_parser.py) 中新增用例，验证以下内容会被正确抽取：

- 学费与住宿费
- 办学地点 / 校区
- 大类招生与分流
- 推免 / 保研通道
- 性别限制
- 单科成绩门槛

## 3. 导入与核验结果

### 3.1 归一化结果

本次从河南章程源文件解析出的归一化规则数为：

- `normalized_count = 11585`

规则类型分布如下：

- `adjustment_policy = 1640`
- `campus_assignment = 1099`
- `cooperative_education = 514`
- `gender_requirement = 796`
- `graduate_recommendation = 60`
- `language_requirement = 752`
- `physical_requirement = 2163`
- `pilot_class_pathway = 264`
- `single_subject_requirement = 943`
- `special_program = 298`
- `subject_selection_reference = 847`
- `tuition_requirement = 2209`

### 3.2 覆盖面核验

导入摘要文件显示：

- 归一化后的院校名共 `2222` 个
- 与当前正式院校库匹配成功 `1851` 个
- 未匹配 `371` 个

这说明章程规则已经明显扩充，但院校主数据别名仍有后续清洗空间。

### 3.3 PostgreSQL 实际入库结果

正式导入后，当前 PostgreSQL 实查：

- `institution_rules = 10115`

按 `rule_type` 查询的当前库内分布为：

- `adjustment_policy = 1367`
- `campus_assignment = 956`
- `cooperative_education = 481`
- `gender_requirement = 682`
- `graduate_recommendation = 59`
- `language_requirement = 675`
- `military_charter = 22`
- `physical_requirement = 1814`
- `pilot_class_pathway = 248`
- `police_charter = 54`
- `single_subject_requirement = 849`
- `special_program = 277`
- `subject_selection_reference = 788`
- `tuition_requirement = 1843`

说明新增规则类型已经实际落入正式库，而不是只停留在解析阶段。

## 4. 本次执行的命令

```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_institution_rule_parser
.\.venv\Scripts\python.exe backend/scripts/import_institution_rules.py --dry-run
.\.venv\Scripts\python.exe backend/scripts/import_institution_rules.py
@'
from backend.database import db_session
with db_session() as conn:
    total = conn.execute("SELECT COUNT(*) AS total FROM institution_rules").fetchone()["total"]
    print(total)
'@ | .\.venv\Scripts\python.exe -
@'
from backend.database import db_session
with db_session() as conn:
    rows = conn.execute("SELECT rule_type, COUNT(*) AS total FROM institution_rules GROUP BY rule_type ORDER BY rule_type").fetchall()
    for row in rows:
        print(f"{row['rule_type']}\t{row['total']}")
'@ | .\.venv\Scripts\python.exe -
```

## 5. 当前结论

这一步已经把 `institution_rules` 从“只覆盖一部分基础章程限制”，推进到“可以稳定解析更多正式约束并真实入库”的状态。

当前可以明确确认的结果是：

- 新增了 6 类高价值章程规则类型
- dry-run 已不再依赖数据库在线
- 河南章程规则归一化规模提升到 `11585`
- PostgreSQL 中当前已有 `10115` 条正式 `institution_rules`

## 6. 剩余问题

- 当前仍有 `371` 个院校名未匹配，需要后续配合 `institutions` 主数据继续补别名或做清洗映射
- `policy_trends` 还没有进入本轮同等级别的扩充，需要继续推进
