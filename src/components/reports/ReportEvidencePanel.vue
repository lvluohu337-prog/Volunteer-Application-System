<script setup>
defineProps({
  resultSource: { type: Object, required: true },
  resultSourceFacts: { type: Array, default: () => [] },
  recommendationTable: { type: Array, default: () => [] },
  topRiskNotes: { type: Array, default: () => [] }
});
</script>

<template>
  <section class="report-evidence-panel" aria-labelledby="report-evidence-title">
    <header>
      <span>证据链审阅</span>
      <h2 id="report-evidence-title">为什么这份方案可信</h2>
    </header>

    <div class="evidence-brief">
      <div>
        <strong>先看依据，再看建议</strong>
        <p>
          本区把系统使用的数据来源、推荐样本量和人工复核重点放在同一处，
          让家长能判断这不是“拍脑袋推荐”，而是一份可追溯、可复核的正式方案。
        </p>
      </div>
      <span>证据完整度</span>
    </div>

    <div class="evidence-grid">
      <article class="evidence-card source-card">
        <span>数据来源</span>
        <strong>{{ resultSource.label || "待确认" }}</strong>
        <p>{{ resultSourceFacts.join(" / ") || "暂未形成完整数据依据。" }}</p>
      </article>

      <article class="evidence-card">
        <span>推荐样本</span>
        <strong>{{ recommendationTable.length }} 个专业组</strong>
        <p>当前方案用于正式填报前逐项复核院校专业组、组内专业接受度和风险边界。</p>
      </article>

      <article class="evidence-card">
        <span>重点复核</span>
        <strong>{{ topRiskNotes.length || 1 }} 项</strong>
        <p>{{ topRiskNotes[0] || "招生章程、专业组和调剂规则仍需人工复核。" }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.report-evidence-panel {
  padding: 24px 0;
}

.report-evidence-panel header {
  margin-bottom: 14px;
}

.report-evidence-panel header span,
.evidence-grid span {
  color: #667085;
  font-size: 13px;
}

.report-evidence-panel h2 {
  margin: 4px 0 0;
  color: #111827;
  font-size: 22px;
  font-weight: 750;
}

.evidence-brief {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  align-items: center;
  margin-bottom: 14px;
  padding: 16px 18px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: inset 4px 0 0 #0f766e;
}

.evidence-brief strong,
.evidence-brief p {
  display: block;
}

.evidence-brief strong {
  color: #111827;
  font-size: 16px;
}

.evidence-brief p {
  max-width: 860px;
  margin: 8px 0 0;
  color: #475467;
  line-height: 1.72;
}

.evidence-brief > span {
  padding: 8px 10px;
  border: 1px solid rgba(181, 107, 45, 0.22);
  border-radius: 6px;
  background: #fff7ed;
  color: #9a5a26;
  font-size: 13px;
  font-weight: 700;
}

.evidence-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.evidence-card {
  padding: 16px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: #ffffff;
}

.source-card {
  border-color: rgba(15, 118, 110, 0.2);
  background: linear-gradient(180deg, #ffffff 0%, #f8fffd 100%);
}

.evidence-grid strong {
  display: block;
  margin-top: 4px;
  color: #111827;
  font-size: 18px;
}

.evidence-grid p {
  margin: 8px 0 0;
  color: #475467;
  line-height: 1.72;
}

@media (max-width: 900px) {
  .evidence-brief {
    grid-template-columns: 1fr;
  }

  .evidence-grid {
    grid-template-columns: 1fr;
  }
}
</style>
