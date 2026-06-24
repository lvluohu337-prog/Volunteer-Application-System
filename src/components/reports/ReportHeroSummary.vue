<script setup>
defineProps({
  title: { type: String, default: "" },
  subtitle: { type: String, default: "" },
  activeProductLabel: { type: String, default: "" },
  ruleSummary: { type: Object, required: true },
  resultSource: { type: Object, required: true },
  resultSourceFacts: { type: Array, default: () => [] },
  hasFormalReportResult: { type: Boolean, default: false },
  exporting: { type: String, default: "" },
  activeDeliveryChannels: { type: Array, default: () => [] }
});

const emit = defineEmits(["export-pdf", "export-word", "view-student"]);
</script>

<template>
  <section class="report-hero-summary" aria-labelledby="report-hero-title">
    <div class="report-cover-bar">
      <div>
        <span class="report-bookmark">正式报告书</span>
        <strong>河南 2026 高考志愿正式规划报告</strong>
      </div>
      <span class="report-seal">已生成</span>
    </div>

    <div class="report-kicker">正式志愿规划报告</div>
    <div class="report-hero-grid">
      <div class="report-hero-main">
        <h1 id="report-hero-title">{{ title || "高考志愿规划报告" }}</h1>
        <p>
          {{
            ruleSummary.finalConclusion ||
            subtitle ||
            "当前报告已生成正式推荐结果，正式填报前仍需完成招生章程、专业组和调剂规则复核。"
          }}
        </p>
        <div class="hero-chip-row" aria-label="报告关键信息">
          <span v-if="activeProductLabel">{{ activeProductLabel }}</span>
          <span>{{ ruleSummary.strategy?.name || "策略待确认" }}</span>
          <span>{{ resultSource.label || "数据状态待确认" }}</span>
        </div>

        <div class="trust-badge-row" aria-label="可信交付依据">
          <span>真实招生数据</span>
          <span>48 专业组方案</span>
          <span>人工复核清单</span>
        </div>
      </div>

      <div class="report-hero-actions" aria-label="报告操作">
        <button type="button" class="ghost-action" @click="emit('view-student')">学生档案</button>
        <button
          v-if="activeDeliveryChannels.includes('word')"
          type="button"
          class="ghost-action"
          :disabled="!hasFormalReportResult || exporting === 'word'"
          @click="emit('export-word')"
        >
          导出 Word
        </button>
        <button
          v-if="activeDeliveryChannels.includes('pdf')"
          type="button"
          class="primary-action"
          :disabled="!hasFormalReportResult || exporting === 'pdf'"
          @click="emit('export-pdf')"
        >
          导出 PDF
        </button>
      </div>
    </div>

    <div class="report-evidence-strip">
      <div>
        <span>分层判断</span>
        <strong>{{ ruleSummary.scoreLevel || "待补充" }}</strong>
      </div>
      <div>
        <span>推荐规模</span>
        <strong>{{ ruleSummary.strategy?.total_choice_target || 48 }} 个专业组</strong>
      </div>
      <div>
        <span>数据依据</span>
        <strong>{{ resultSourceFacts.join(" / ") || "待补充" }}</strong>
      </div>
    </div>
  </section>
</template>

<style scoped>
.report-hero-summary {
  padding: 30px 34px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background:
    linear-gradient(90deg, rgba(15, 118, 110, 0.08), transparent 34%),
    linear-gradient(180deg, #ffffff 0%, #fbfcf8 100%);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
}

.report-cover-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.1);
}

.report-cover-bar div,
.report-cover-bar strong,
.report-bookmark {
  display: block;
}

.report-cover-bar strong {
  margin-top: 6px;
  color: #111827;
  font-size: 18px;
  letter-spacing: 0;
}

.report-bookmark {
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
}

.report-seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 68px;
  height: 68px;
  border: 2px solid rgba(181, 107, 45, 0.72);
  border-radius: 50%;
  color: #9a5a26;
  font-size: 15px;
  font-weight: 800;
}

.report-kicker {
  margin-bottom: 12px;
  color: #667085;
  font-size: 13px;
}

.report-hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
}

.report-hero-main h1 {
  margin: 0;
  color: #111827;
  font-size: 30px;
  font-weight: 750;
  line-height: 1.22;
}

.report-hero-main p {
  max-width: 860px;
  margin: 12px 0 0;
  color: #344054;
  font-size: 15px;
  line-height: 1.85;
}

.hero-chip-row,
.report-hero-actions,
.report-evidence-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-chip-row {
  margin-top: 16px;
}

.trust-badge-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 150px));
  gap: 10px;
  margin-top: 14px;
}

.trust-badge-row span {
  padding: 9px 12px;
  border: 1px solid rgba(15, 118, 110, 0.18);
  border-radius: 6px;
  background: rgba(240, 253, 250, 0.72);
  color: #115e59;
  font-size: 13px;
  font-weight: 700;
  text-align: center;
}

.hero-chip-row span,
.report-evidence-strip div {
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.86);
}

.hero-chip-row span {
  padding: 7px 10px;
  color: #475467;
  font-size: 13px;
}

.report-hero-actions {
  align-content: flex-start;
  justify-content: flex-end;
}

.primary-action,
.ghost-action {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 6px;
  font: inherit;
  cursor: pointer;
}

.primary-action {
  border: 1px solid #0f766e;
  background: #0f766e;
  color: #ffffff;
}

.ghost-action {
  border: 1px solid rgba(15, 23, 42, 0.16);
  background: #ffffff;
  color: #334155;
}

.primary-action:disabled,
.ghost-action:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.report-evidence-strip {
  margin-top: 24px;
}

.report-evidence-strip div {
  min-width: 180px;
  padding: 10px 12px;
}

.report-evidence-strip span,
.report-evidence-strip strong {
  display: block;
}

.report-evidence-strip span {
  color: #667085;
  font-size: 12px;
}

.report-evidence-strip strong {
  margin-top: 4px;
  color: #111827;
  font-size: 15px;
}

@media (max-width: 900px) {
  .report-hero-summary {
    padding: 24px;
  }

  .report-hero-grid {
    grid-template-columns: 1fr;
  }

  .report-hero-actions {
    justify-content: flex-start;
  }

  .trust-badge-row {
    grid-template-columns: 1fr;
  }
}
</style>
