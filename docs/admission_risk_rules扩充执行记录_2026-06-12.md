# admission_risk_rules 扩充执行记录

执行日期：`2026-06-12`

## 1. 本次目标

- 扩充河南当前正式库中的 `admission_risk_rules`
- 让风险规则文案从“原文碎片”变成“可直接展示给用户的正式风险提示”
- 保证 `import_henan_policy_rules.py` 重复执行时不会因为文案调整把旧规则越堆越多

## 2. 本次做了什么

### 2.1 扩充政策来源

在 [backend/policy_importer.py](D:/2026workspace/Volunteer%20Application%20System/backend/policy_importer.py) 中新增接入了这些河南政策文件：

- `河南省2026年普通高招报名工作相关事宜问答.docx`
- `河南省教育厅关于做好2025年高等职业教育单独考试招生和技能拔尖人才免试入学工作的通知- 文件通知 - 河南省教育厅.pdf`
- `河南省教育厅关于做好2026年普通高等学校对口招收中等职业学校毕业生工作的通知- 文件通知 - 河南省教育厅.pdf`

同时补充了已有体育类、艺术类政策的细分风险规则。

### 2.2 新增的风险类型

本次新增的核心风险类型包括：

- `special_registration_review`
- `sports_score_structure`
- `arts_category_alignment`
- `single_exam_one_choice`
- `single_exam_skill_test`
- `single_exam_charter_review`
- `counterpart_eligibility`
- `counterpart_major_alignment`
- `counterpart_sports_exam`
- `counterpart_arts_exam`

### 2.3 清洗规则文案

调整了 [backend/policy_importer.py](D:/2026workspace/Volunteer%20Application%20System/backend/policy_importer.py) 的抽取逻辑：

- `risk_message` 优先落 `default_message`，不再直接把“的说明和解释”“网站导航残片”这类原文噪音写进正式规则
- 同时把 `source_excerpt`、`policy_topic` 保留到 `raw_json`，方便后续回溯政策依据
- 对政策摘要行增加了噪音过滤，减少门户页眉页脚和导航文字进入数据表

### 2.4 修复重复导入膨胀问题

调整了 [backend/scripts/import_henan_policy_rules.py](D:/2026workspace/Volunteer%20Application%20System/backend/scripts/import_henan_policy_rules.py)：

- 重新导入前，先按 `policy_key` 替换同源 `policy_trends`
- 重新导入前，先按 `raw_json.policy_key` 模式替换同源 `admission_risk_rules`

这样同一批政策规则可以重复导入，而不会从 `24` 变成 `48`

## 3. 导入结果

### 导入前

- `admission_risk_rules = 14`
- `policy_trends = 9`

### 导入后

- `admission_risk_rules = 24`
- `policy_trends = 12`

### 幂等性核验

连续执行两次：

```powershell
.\.venv\Scripts\python.exe backend/scripts/import_henan_policy_rules.py
```

二次执行后再次回查：

- `admission_risk_rules = 24`
- `policy_trends = 12`

说明替换逻辑已经生效，没有重复膨胀。

## 4. 本次执行的命令

```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_policy_importer
.\.venv\Scripts\python.exe backend/scripts/import_henan_policy_rules.py --dry-run
.\.venv\Scripts\python.exe backend/scripts/import_henan_policy_rules.py
.\.venv\Scripts\python.exe backend/scripts/import_henan_policy_rules.py
.\.venv\Scripts\python.exe -m unittest backend.tests.test_policy_importer backend.tests.test_province_support backend.tests.test_province_readiness
```

## 5. 当前结论

这一步已经把河南风险规则库从“只有 14 条、且部分文案直接是原文碎片”，推进到“24 条、可重复导入、可直接用于前端/报告展示”的状态。

仍然没有在本次完成的，是后续两块：

- `institution_rules` 的继续补强
- `policy_trends` 的继续扩充与更细颗粒度解释
