<script setup>
defineProps({
  firstChoice: { type: Object, default: null },
  ruleSummary: { type: Object, required: true },
  topRiskNotes: { type: Array, default: () => [] },
  formatScore: { type: Function, required: true },
  formatRank: { type: Function, required: true },
  formatRankGap: { type: Function, required: true }
});
</script>

<template>
  <section class="report-core-conclusion" aria-labelledby="core-conclusion-title">
    <header>
      <span>核心结论</span>
      <h2 id="core-conclusion-title">先看结论，再看明细</h2>
    </header>

    <div class="conclusion-grid">
      <article class="primary-conclusion">
        <span>第一志愿建议</span>
        <h3>{{ firstChoice?.institutionName || "待补充院校" }}</h3>
        <p>
          {{ firstChoice?.majorName || "待补充专业" }}
          <template v-if="firstChoice?.planGroupCode"> / {{ firstChoice.planGroupCode }}</template>
        </p>
        <dl>
          <div>
            <dt>最低分</dt>
            <dd>{{ formatScore(firstChoice?.minScore) }}</dd>
          </div>
          <div>
            <dt>最低位次</dt>
            <dd>{{ formatRank(firstChoice?.minRank) }}</dd>
          </div>
          <div>
            <dt>位次差</dt>
            <dd>{{ formatRankGap(firstChoice?.rankGap) }}</dd>
          </div>
        </dl>
      </article>

      <article>
        <span>策略分布</span>
        <h3>{{ ruleSummary.strategy?.name || "策略待确认" }}</h3>
        <p>
          {{
            ruleSummary.strategy?.note ||
            ruleSummary.finalConclusion ||
            "当前策略说明待补充，正式填报前应结合 48 个院校专业组逐项复核。"
          }}
        </p>
      </article>

      <article>
        <span>重点风险</span>
        <ul>
          <li v-for="item in topRiskNotes.slice(0, 3)" :key="item">{{ item }}</li>
          <li v-if="!topRiskNotes.length">正式填报前仍需复核招生章程、专业组规则和调剂边界。</li>
        </ul>
      </article>
    </div>
  </section>
</template>

<style scoped>
.report-core-conclusion {
  padding: 24px 0;
}

.report-core-conclusion header {
  margin-bottom: 16px;
}

.report-core-conclusion header span,
.conclusion-grid article > span {
  color: #667085;
  font-size: 13px;
}

.report-core-conclusion h2,
.conclusion-grid h3 {
  margin: 4px 0 0;
  color: #111827;
}

.report-core-conclusion h2 {
  font-size: 22px;
  font-weight: 750;
}

.conclusion-grid {
  display: grid;
  grid-template-columns: minmax(280px, 1.18fr) repeat(2, minmax(220px, 1fr));
  gap: 16px;
}

.conclusion-grid article {
  padding: 18px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: #ffffff;
}

.primary-conclusion {
  border-color: rgba(15, 118, 110, 0.28) !important;
  box-shadow: inset 3px 0 0 #0f766e;
}

.conclusion-grid p,
.conclusion-grid li {
  color: #475467;
  line-height: 1.72;
}

.conclusion-grid p {
  margin: 10px 0 0;
}

.conclusion-grid ul {
  margin: 10px 0 0;
  padding-left: 18px;
}

dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 16px 0 0;
}

dt {
  color: #667085;
  font-size: 12px;
}

dd {
  margin: 4px 0 0;
  color: #111827;
  font-weight: 700;
}

@media (max-width: 1100px) {
  .conclusion-grid {
    grid-template-columns: 1fr;
  }
}
</style>
