# TESTING

## 1. 当前测试范围

当前仓库还没有独立的 `backend/tests` 或前端自动化测试目录，因此本文件主要覆盖：

- 环境准备
- 数据导入验证
- 后端接口冒烟验证
- 前端关键页面联调
- 构建与导出链路检查

如果要做“严格联调”，建议关闭前端 mock 回退。

---

## 2. 安装依赖

### 前端

```bash
npm install
```

### 后端

```bash
python -m pip install -r backend/requirements.txt
```

当前后端依赖重点：

- `fastapi`
- `uvicorn`
- `psycopg[binary]`
- `pypdf`

说明：

- 基础 Excel 导入脚本未额外依赖 `pandas` 或 `openpyxl`。
- 后端会自动尝试加载项目根目录下的 `.env` 和 `.env.local`。

---

## 3. 环境变量建议

建议先基于 `.env.example` 创建本地 `.env`。

关键项：

```bash
VITE_API_BASE_URL=/api
VITE_USE_MOCK=false
DATABASE_URL=postgresql://gaokao_app:YOUR_PASSWORD@127.0.0.1:5432/gaokao_planning
```

注意：

- `VITE_USE_MOCK` 如果不是 `false`，部分前端请求在失败时会回退到 mock/fallback 数据，容易掩盖真实联调问题。
- 当前仓库只支持 PostgreSQL，不再保留 SQLite 回退模式。

---

## 4. 数据导入验证

### 4.1 基础数据导入

原始文件：

- `data_assets/raw/歪歪志愿馆_高考志愿系统_基础数据包.xlsx`

执行命令：

```bash
python -m backend.scripts.import_foundation_data
```

验证点：

- 生成 `data_assets/imported/import_summary.json`
- 生成 `data_assets/imported/excel_sheet_overview.json`
- 生成基础中间文件 `JSON / CSV`
- 基础表可重复导入，不应无限插入重复数据

当前基础数据实际导入结果：

- `major_categories`: 14
- `city_industries`: 12
- `sample_students`: 12
- `report_template_fields`: 11

### 4.2 河南招生主数据导入

执行命令：

```bash
python -m backend.scripts.import_henan_admissions_data
```

仅做结构和样例验证时可用：

```bash
python -m backend.scripts.import_henan_admissions_data --dry-run
python -m backend.scripts.import_henan_admissions_data --limit 200
```

验证文件：

- `data_assets/imported/henan_admissions/henan_admissions_import_summary.json`
- `data_assets/imported/henan_admissions/*.sample.json`
- `data_assets/imported/henan_admissions/*.sample.csv`

当前数据库中的实际行数：

- `institutions`: 3441
- `majors`: 50797
- `score_segments`: 1198
- `admission_plans`: 194285
- `institution_admission_scores`: 16278
- `major_admission_scores`: 130679
- `subject_requirements`: 60449

备注：

- 导入逻辑已实现 `ON CONFLICT` upsert，可重复执行。
- `province_batches` 目前仍是已建表、未补数状态。

### 4.3 河南政策 / 章程规则导入

执行命令：

```bash
python -m backend.scripts.import_henan_policy_rules
```

仅做小样本验证时可用：

```bash
python -m backend.scripts.import_henan_policy_rules --dry-run --limit-docs 2
```

验证文件：

- `data_assets/imported/henan_policy_rules/henan_policy_rules_import_summary.json`
- `data_assets/imported/henan_policy_rules/*.sample.json`
- `data_assets/imported/henan_policy_rules/*.sample.csv`

当前数据库中的实际行数：

- `institution_rules`: 133
- `admission_risk_rules`: 14
- `policy_trends`: 9

---

## 5. 启动服务

### 5.1 启动后端

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl.exe http://127.0.0.1:8000/api/health
```

期望结果：

- 返回 `200`
- 响应体中的 `data.status` 为 `ok`

### 5.2 启动前端

```bash
npm run dev
```

默认访问地址通常为：

- `http://127.0.0.1:5173`
- 或终端输出的 Vite 本地地址

---

## 6. 后端接口冒烟

### 6.1 基础接口

```bash
curl.exe "http://127.0.0.1:8000/api/health"
curl.exe "http://127.0.0.1:8000/api/dashboard"
curl.exe "http://127.0.0.1:8000/api/intake/template"
curl.exe "http://127.0.0.1:8000/api/foundation/majors"
curl.exe "http://127.0.0.1:8000/api/foundation/cities"
curl.exe "http://127.0.0.1:8000/api/foundation/sample-students"
curl.exe "http://127.0.0.1:8000/api/foundation/report-template-fields"
curl.exe "http://127.0.0.1:8000/api/foundation/admissions-schema"
```

### 6.2 获取可用学生 ID

```bash
curl.exe "http://127.0.0.1:8000/api/students?page=1&page_size=1"
```

如果返回至少一条学生记录，记下第一条 `id`，后续替换下面的 `{studentId}`。

### 6.3 真实学生链路接口

```bash
curl.exe "http://127.0.0.1:8000/api/students"
curl.exe "http://127.0.0.1:8000/api/students/{studentId}"
curl.exe "http://127.0.0.1:8000/api/students/{studentId}/scores"
curl.exe "http://127.0.0.1:8000/api/analysis/student/{studentId}"
curl.exe "http://127.0.0.1:8000/api/majors/student/{studentId}"
curl.exe "http://127.0.0.1:8000/api/plans/student/{studentId}"
curl.exe "http://127.0.0.1:8000/api/reports/student/{studentId}?product_code=399"
```

重点检查：

- `/api/analysis/student/{studentId}` 是否返回 `metrics`、`buckets`、`policyHighlights`
- `/api/plans/student/{studentId}` 是否返回 `columns`
- `/api/reports/student/{studentId}` 是否返回 `outline`、`sections`、`reportJson`

### 6.4 demo 报告接口

```bash
curl.exe "http://127.0.0.1:8000/api/demo-reports/99?sample_student_id=1"
curl.exe "http://127.0.0.1:8000/api/demo-reports/399?sample_student_id=1"
```

这两条接口仍然保留，适合快速验证样例学生驱动的演示报告。

### 6.5 咨询师备注接口

```powershell
$body = @{
  product_code = "399"
  note_type = "advisor_comment"
  note_title = "联调备注"
  note_content = "这是一次接口冒烟测试备注。"
  author_name = "测试老师"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/reports/student/{studentId}/advisor-notes" `
  -ContentType "application/json" `
  -Body $body
```

期望结果：

- 返回 `200`
- 刷新报告接口后，`advisorNotes` 数组长度增加

### 6.6 导出接口

```powershell
$body = @{
  reportVersion = "399"
  reviewedBy = "测试老师"
  includeSignature = $true
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/reports/student/{studentId}/export/pdf" `
  -ContentType "application/json" `
  -Body $body

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/reports/student/{studentId}/export/word" `
  -ContentType "application/json" `
  -Body $body
```

当前行为说明：

- `pdf` 导出会生成真实 `PDF` 文件
- `word` 导出会生成真实 `DOCX` 文件
- 文件会写入 `data_assets/generated_reports/`
- 同时会新增导出留痕记录

这一步验证的是“正式交付文件与留痕链路”。

---

## 7. 前端关键页面联调

启动前后端后，建议按下面顺序手工走一遍：

### 7.1 学生管理链路

- `/students`
- `/intake`
- `/students/{studentId}`

检查点：

- 学生列表能正确分页、筛选、跳详情
- 新建或编辑学生后，能回到列表看到更新
- 生日和出生时辰填写后，能自动补全星座/四柱/偏好建议

### 7.2 分析与志愿链路

- `/analysis?studentId={studentId}`
- `/majors?studentId={studentId}`
- `/plan?studentId={studentId}`

检查点：

- 分析页能展示指标卡、冲稳保、规则判断、政策摘要
- 专业页能展示真实推荐结果
- 志愿页能展示 `冲 / 稳 / 保` 列表

### 7.3 报告链路

- `/reports?studentId={studentId}&productCode=99`
- `/reports?studentId={studentId}&productCode=399`
- `/reports?studentId={studentId}&productCode=999`

检查点：

- 可切换报告档位
- `reportJson` 模块区正常渲染
- 咨询师备注可保存
- 导出后可看到新的交付记录

### 7.4 基础数据与 demo 页面

- `/base-data`
- `/demo-reports`
- `/settings`

检查点：

- 基础数据页能看到 4 类基础导入数据
- demo 页面仍能基于样例学生生成 99/399 演示报告
- 设置页能正常加载后端返回内容

---

## 8. 构建检查

执行：

```bash
npm run build
```

期望结果：

- Vite 构建成功
- 生成 `dist/` 产物

---

## 9. 当前已验证事实

截至 2026-05-29，仓库现状可以确认：

- 默认数据库引擎为 `PostgreSQL`
- 招生核心表共 `11` 张，除 `province_batches` 外均已有数据
- 真实学生报告链路已可返回 `reportJson`
- 咨询师备注、导出留痕、正式交付文件目录均已接通
- demo 报告链路仍保留可用

当前仍未覆盖的质量空白：

- 没有正式的自动化测试目录
- 没有导入回归测试
- 没有规则引擎断言测试
- 没有最终版 PDF/Word 渲染验收流程

---

## 10. 常见问题

### 1) 前端页面看起来“能用”，但其实没有连上真实后端

处理方式：

- 检查 `.env` 中是否把 `VITE_USE_MOCK` 设成了 `false`
- 打开浏览器网络面板，确认请求真的打到了 `/api/*`

### 2) 后端能启动，但查询不到招生数据

处理方式：

- 先跑 `python -m backend.scripts.import_henan_admissions_data`
- 再跑 `python -m backend.scripts.import_henan_policy_rules`
- 用 `/api/foundation/admissions-schema` 检查各表 `row_count`

### 3) 报告导出成功了，但目录里不是 `.pdf` 或 `.docx`

处理方式：

- 这不再是当前实现预期
- 现阶段导出接口应直接产出正式 `PDF / DOCX` 文件；如果没有，请优先检查是否仍在运行旧代码

### 4) 构建时或导入时行为和文档不一致

处理方式：

- 先确认是否仍引用旧 README、旧测试脚本或过时的本地数据库说明
- 以本文件和当前代码为准，不要再参考历史阶段文档
