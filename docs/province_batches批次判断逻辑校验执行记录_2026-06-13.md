# province_batches 批次判断逻辑校验执行记录

执行日期：`2026-06-13`

## 1. 本次目标

- 校验 `province_batches` 导入后，推荐链路是否真正使用了批次线
- 修复学生录入批次与真实招生表批次口径不一致导致的误判
- 让“本科批 / 专科批 / 本科提前批”在当前河南真实库里具备可解释、可测试的匹配逻辑

## 2. 发现的问题

当前前端学生录入使用的是较粗口径：

- `本科提前批`
- `本科批`
- `专科批`

但真实招生表和批次线表中的批次口径更细，例如：

- `本科一批`
- `本科二批`
- `本科三批`
- `专项计划本科批`
- `体育类本科`
- `专科批`

如果不做批次映射与批次线判定，会出现两类问题：

- 学生明明选择了 `本科批`，却因为真实数据是 `本科一批 / 本科二批` 而误判为无候选
- 学生分数没过本科线，系统仍可能继续在真实本科批数据里检索，导致“逻辑上不该出现的本科推荐”

## 3. 本次做了什么

### 3.1 在 admissions_engine 中补齐批次归一化与批次线判定

在 [backend/admissions_engine.py](D:/2026workspace/Volunteer%20Application%20System/backend/admissions_engine.py) 中新增了这几类逻辑：

- 学生录入批次归一化：`本科批 / 本科提前批 / 专科批 / 综合评价 / 待定`
- 真实批次分组判断：普通本科、提前批、专项本科、体育本科、艺术本科、普通专科等
- 基于 `province_batches` 的批次线判定
- 根据当前分数计算 `effective_batch_codes`

核心思路是：

- 先根据学生录入批次决定“候选批次族”
- 再根据河南已导入的批次线判断当前分数是否达到该批次要求
- 最终把可用批次收敛到真实候选 SQL 过滤中

### 3.2 推荐查询正式接入批次过滤

在候选查询阶段，把批次过滤真正接入了 `major_admission_scores` 的查询条件。

这样不是“查出来后再备注一下批次”，而是：

- 本科批学生只会进入匹配后的本科批次候选
- 专科批学生只会进入匹配后的专科批次候选
- 如果当前分数未过所选批次线，普通本科 / 专科候选会直接被阻断

### 3.3 fallback 原因补齐为“未达到所选批次线”

调整了 [backend/planning_repository.py](D:/2026workspace/Volunteer%20Application%20System/backend/planning_repository.py) 中的 `_fallback_reason_text`：

- 当 `batch_requirement_met = False` 时
- 返回“当前分数尚未达到所选批次对应批次线”

这样前端和报告端拿到的 fallback 原因会更准确，不再把“本来没过批次线”与“数据未命中”混成一种情况。

## 4. 新增测试

新增测试文件：

- [backend/tests/test_admissions_engine_batch_logic.py](D:/2026workspace/Volunteer%20Application%20System/backend/tests/test_admissions_engine_batch_logic.py)

覆盖了这些关键场景：

- `本科批` 只匹配普通本科，不匹配专项 / 体育 / 专科
- `本科批` 会根据批次线把 `本科一批 / 本科二批` 进一步收敛
- 当前分数未达到所选本科线时，返回 `batch_requirement_met = False`
- 上下文会写入 `effective_batch_codes`

## 5. 执行结果

### 5.1 单测结果

执行：

```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_admissions_engine backend.tests.test_admissions_engine_batch_logic backend.tests.test_planning_repository_structured_report
```

结果：

- `Ran 10 tests ... OK`

### 5.2 真实库样例回归

用河南 / 物理类样例学生做了 3 组真实回归：

1. `本科批`，`500` 分

- `effective_batch_codes = ['本科二批']`
- `batch_requirement_met = True`
- `candidate_count = 20`

2. `本科批`，`380` 分

- `effective_batch_codes = []`
- `batch_requirement_met = False`
- `candidate_count = 0`
- fallback 原因变为“当前分数尚未达到所选本科批对应批次线”

3. `专科批`，`380` 分

- `effective_batch_codes = ['专科批']`
- `batch_requirement_met = True`
- `candidate_count = 20`

这说明当前批次判断链路已经能区分：

- “本科批但只够二本线”
- “本科批但还没过本科线”
- “专科批且已过专科线”

## 6. 当前结论

这一步已经把 `province_batches` 从“只是导入了表”，推进到“真实参与批次判断并可回归验证”的状态。

当前可以明确确认的结果是：

- `province_batches = 142`
- 推荐链路已接入批次线与批次映射逻辑
- `本科批 / 专科批` 已不再只是前端展示字段
- fallback 原因能区分“未达到所选批次线”

## 7. 后续建议

- 当前 `本科提前批` 仍是较宽口径，后续如要继续正式化，可再细分为军校 / 公安 / 体育 / 艺术 / 专项等子类型
- 之后就可以按清单顺序进入前端稳定性：优先收口静默 mock / demo fallback
