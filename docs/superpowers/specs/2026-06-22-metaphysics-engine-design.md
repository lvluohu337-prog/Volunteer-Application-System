# 命理引擎升级设计（四柱先准，紫微预留）

## 1. 背景

当前项目的画像辅助模块位于 `backend/intake_inference.py` 与 `backend/portrait_service.py`。它已经能根据阳历生日、出生时辰生成：

- 星座
- 四柱（年/月/日/时）
- 五行倾向
- 性格标签
- 兴趣方向 / 地域偏好 / 发展目标建议

但这套实现本质上仍是“轻量规则推导”：

- 月柱使用固定日期近似节气，不是真实节气时刻
- 时柱未做真太阳时修正
- 未处理晚子时按次日排盘的规则
- 五行判断仅做天干地支计数，未做更严谨的输入归一化

用户要求参考 `E:\work\ziwei-doushu` 项目中的命理实现，优化当前项目的算法准确性，并为后续引入紫微斗数能力做准备。

## 2. 目标

第一阶段目标：

1. 在不大改现有前端页面的前提下，提升四柱八字计算准确性
2. 保持现有 `derived_profile` 输出结构兼容，避免打断 `IntakePage`、`AnalysisPage`、`ReportsPage`
3. 为第二阶段引入紫微斗数能力预留后端桥接能力
4. 仅影响新建 / 编辑 / 重新触发推导的学生，不批量回刷历史画像数据

第二阶段目标（本次不实现）：

1. 接入紫微斗数排盘结果
2. 将紫微斗数作为独立辅助画像层进入解释逻辑
3. 再决定是否参与专业方向推荐的解释层，而非录取规则层

## 3. 非目标

本次不做以下事情：

- 不重写前端录入页结构
- 不直接展示完整紫微命盘 UI
- 不批量重算历史学生数据
- 不把命理结果纳入正式录取推荐的硬规则计算
- 不在本阶段做复杂的命理格局、用神、喜忌、藏干权重建模

## 4. 参考项目结论

对 `E:\work\ziwei-doushu` 的只读分析后，确认其最值得借鉴的部分不是 UI，而是以下底层能力：

1. `lunar-javascript`
   - 提供更可靠的农历、节气、干支相关能力
2. 真太阳时修正
   - 根据经度做时差修正
3. 晚子时次日规则
   - `23:00-23:59` 作为次日处理
4. 紫微斗数排盘入口
   - 后续可通过 `iztro` + `lunar-javascript` 生成命盘

结论：

- 第一阶段四柱升级优先借 `lunar-javascript` 与时间归一化规则
- 第二阶段再接 `iztro` 排紫微命盘
- 不建议整包搬运 `ziwei-doushu`

## 5. 方案选择

已确认采用的路线：

- 总体方向：`C`
  - 四柱先做准，紫微后补
- 技术接法：`C`
  - 四柱在 Python 侧升级
  - 紫微斗数通过 JS/TS 能力旁路接入
- 第一阶段展示：`A`
  - 只替换底层算法，界面尽量不变
- 历史数据策略：`A`
  - 不回刷历史数据，仅对新建 / 编辑 / 重算生效

## 6. 总体设计

### 6.1 模块边界

第一阶段新增三个清晰边界：

1. `Node 命理桥接层`
   - 职责：调用 `lunar-javascript`，输出标准化四柱结果
   - 不负责生成前端展示文案
   - 不负责专业推荐

2. `Python 命理归一化层`
   - 职责：调用 Node 桥接层，拿到更准确的四柱输入
   - 负责兼容已有 `derive_birth_profile()` 对外接口
   - 负责失败回退与错误边界

3. `画像映射层`
   - 职责：将标准化四柱 / 五行结果映射为当前项目的 `derived_profile`
   - 保留现有 `portrait_service.py` 的消费结构
   - 不直接耦合 Node 运行细节

### 6.2 文件规划

建议新增 / 调整如下：

- `backend/metaphysics_profile.py`
  - 新的命理主入口
  - 对外提供：`derive_birth_profile_v2(...)`

- `backend/metaphysics_mapping.py`
  - 四柱标准结果 -> 当前画像结构

- `backend/intake_inference.py`
  - 第一阶段保留兼容入口
  - 内部逐步改为委托 `metaphysics_profile.py`

- `tools/metaphysics_bridge/`
  - `package.json`
  - `bridge.js` 或 `bridge.mjs`
  - 负责调用 `lunar-javascript`

- `backend/tests/test_metaphysics_profile.py`
  - 新增四柱准确性回归测试

- `backend/tests/test_intake_inference_compat.py`
  - 新增兼容输出结构测试

第二阶段预留：

- `tools/metaphysics_bridge/ziwei_chart.js`
- `backend/ziwei_profile.py`

## 7. 第一阶段数据流

### 输入

当前仍沿用：

- 阳历生日 `birthday`
- 出生时间 `birth_time`
- 后续可扩展：
  - 出生省份 / 城市
  - 经度

### 处理流程

1. Python 收到生日、时辰
2. Python 调用 Node 桥接层
3. Node 层执行：
   - 日期合法性校验
   - 晚子时次日归一化
   - 真太阳时归一化
   - 基于 `lunar-javascript` 生成更准确的干支 / 节气相关结果
4. Node 输出标准化 payload
5. Python 将 payload 映射为现有 `derived_profile`
6. `portrait_service.py` 继续消费兼容结构

### 输出

第一阶段对外仍保持兼容：

- `birthday`
- `birthTime`
- `constellation`
- `pillars`
- `hourBranchLabel`
- `wuxing`
- `profile`
- `autofill`
- `disclaimer`

必要时新增但不强依赖的字段：

- `normalizedBirthDate`
- `normalizedBirthTime`
- `trueSolarTime`
- `longitude`
- `normalizationNotes`
- `engineVersion`

## 8. 四柱准确性升级范围

第一阶段必须修正：

1. 年柱按立春切换
2. 月柱按真实节气而非固定日期近似
3. 时柱按真太阳时而非仅按北京时间
4. 晚子时（23:00-23:59）按次日处理
5. 五行统计基于修正后的四柱结果重算

第一阶段暂不做：

1. 用神忌神
2. 格局判断
3. 藏干权重
4. 旺衰深度建模
5. 八字断命文案体系

## 9. 紫微斗数预留方案

第二阶段不直接嵌入现有录入页结构，但第一阶段要预留好能力接口。

预留原则：

1. `Node 桥接层` 未来可扩展两个命令：
   - `bazi`
   - `ziwei`

2. Python 层未来可扩展：
   - `derive_birth_profile_v2()`：四柱画像
   - `derive_ziwei_profile()`：紫微画像

3. 前端暂不要求修改页面布局，只需后端结构能承载未来扩展字段

建议未来紫微画像独立输出：

- `ziweiChartSummary`
- `ziweiTraits`
- `ziweiHints`
- `ziweiDisclaimer`

避免直接和当前 `derived_profile.profile.personalityTraits` 混成一锅。

## 10. 兼容与回退策略

### 10.1 历史数据兼容

按用户要求，第一阶段不批量回刷老数据。

规则如下：

1. 新建学生：使用新算法
2. 编辑学生：若生日/时辰触发重算，则使用新算法
3. 老学生未编辑：保留旧画像数据

### 10.2 运行时回退

若 Node 桥接层不可用：

1. Python 返回明确错误上下文
2. 允许保守回退到旧算法，但必须打标记：
   - `engineVersion = legacy_fallback`
3. 前端不应静默冒充新算法结果

推荐第一阶段在正式环境中：

- 开发环境允许回退
- 正式环境优先记录日志并显式标记

## 11. 验证方案

第一阶段至少覆盖以下测试：

### 11.1 四柱准确性测试

1. 立春前后年柱切换
2. 节气边界月柱切换
3. 晚子时跨日
4. 经度差异导致真太阳时时辰变化
5. 无出生时辰时仍能稳定输出前三柱

### 11.2 兼容输出测试

1. `derive_birth_profile()` 返回字段完整
2. `autofill` 结构与现有前端兼容
3. `AnalysisPage` / `ReportsPage` 使用的 `derivedProfile` 结构不破

### 11.3 回退测试

1. Node 桥接层异常时的错误处理
2. 可选回退路径是否正确标记 `engineVersion`

## 12. 风险与应对

### 风险 1：Node 与 Python 双栈维护复杂

应对：

- Node 只负责底层计算
- Python 负责对外契约与业务兼容
- 严禁把推荐逻辑写进桥接层

### 风险 2：前端表单缺少经度输入

应对：

- 第一阶段先允许无经度时按默认时区逻辑处理
- 后续再补出生地/经度输入增强

### 风险 3：历史学生画像新旧算法混用

应对：

- 增加 `engineVersion`
- 后端/报告层能够识别当前画像来自哪套算法

### 风险 4：紫微能力过早混入现有推荐逻辑

应对：

- 第一阶段只预留接口，不进推荐打分主路径
- 第二阶段单独评审其解释边界

## 13. 分阶段实施建议

### Phase 1

- 搭 Node 桥接层
- 接入 `lunar-javascript`
- 升级四柱/时间归一化
- 保持现有前端与 `derived_profile` 兼容

### Phase 2

- 接入 `iztro`
- 生成紫微命盘摘要
- 后端新增独立紫微画像结构

### Phase 3

- 评估是否将紫微摘要纳入专业方向解释层
- 严禁进入正式录取规则计算层

## 14. 本次实现边界结论

本次进入实现时，只做 Phase 1。

也就是说，真正会落地的第一批改动应该是：

1. 建立 Node 命理桥接层
2. 用 `lunar-javascript` 重做四柱输入归一化
3. Python 保持现有接口兼容
4. 新增精准性和兼容性测试

不做：

1. 紫微斗数页面
2. 紫微斗数 UI
3. 紫微与专业推荐深度融合

