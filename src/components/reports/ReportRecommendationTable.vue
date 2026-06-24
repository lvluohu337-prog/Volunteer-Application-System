<script setup>
defineProps({
  recommendationTable: {
    type: Array,
    default: () => []
  },
  bucketDefinitions: {
    type: Array,
    default: () => []
  },
  recommendationBuckets: {
    type: Object,
    required: true
  },
  firstChoice: {
    type: Object,
    default: null
  },
  formatScore: {
    type: Function,
    required: true
  },
  formatRank: {
    type: Function,
    required: true
  },
  formatGap: {
    type: Function,
    required: true
  },
  formatRankGap: {
    type: Function,
    required: true
  },
  riskTagType: {
    type: Function,
    required: true
  }
});

function isFirstChoiceRow(row, firstChoice) {
  if (!row || !firstChoice) {
    return false;
  }
  return (
    row.institutionName === firstChoice.institutionName &&
    row.majorName === firstChoice.majorName &&
    (row.planGroupCode || "") === (firstChoice.planGroupCode || "")
  );
}
</script>

<template>
  <section class="formal-report-block">
    <header class="section-head">
      <div>
        <strong>48 个院校专业组正式方案</strong>
        <span>按险、冲、稳、保、垫、兜分层阅读。每一行都保留分数、位次、专业组和风险依据，便于正式填报前逐项复核。</span>
      </div>
      <el-tag type="primary">
        共 {{ recommendationTable.length }} 个专业组建议
      </el-tag>
    </header>

    <div class="bucket-summary-grid">
      <article
        v-for="bucket in bucketDefinitions"
        :key="bucket.key"
        class="bucket-stat-card"
      >
        <div class="bucket-stat-head">
          <el-tag :type="bucket.tagType">{{ bucket.shortTitle }}</el-tag>
          <strong>{{ bucket.title }}</strong>
        </div>
        <p>{{ bucket.description }}</p>
        <span>{{ recommendationBuckets[bucket.key].length }} 个专业组</span>
      </article>
    </div>

    <article v-if="firstChoice" class="first-choice-card">
      <header class="section-head compact">
        <div>
          <strong>第一志愿建议</strong>
          <span>建议优先作为正式填报时的主力样本，再结合家长沟通和调剂边界做最终确认。</span>
        </div>
        <el-tag :type="riskTagType(firstChoice.riskLevel)">
          {{ firstChoice.riskLabel || "待复核" }}
        </el-tag>
      </header>

      <div class="first-choice-main">
        <div>
          <h3>{{ firstChoice.institutionName }}</h3>
          <p>
            {{ firstChoice.majorName }}
            <template v-if="firstChoice.planGroupCode"> / {{ firstChoice.planGroupCode }}</template>
          </p>
          <span>{{ firstChoice.cityText || firstChoice.city || firstChoice.province || "待补充城市" }}</span>
        </div>
        <div class="choice-metrics">
          <div>
            <small>历史最低分</small>
            <strong>{{ formatScore(firstChoice.minScore) }}</strong>
          </div>
          <div>
            <small>历史最低位次</small>
            <strong>{{ formatRank(firstChoice.minRank) }}</strong>
          </div>
          <div>
            <small>位次差</small>
            <strong>{{ formatRankGap(firstChoice.rankGap) }}</strong>
          </div>
          <div>
            <small>调剂态度</small>
            <strong>{{ firstChoice.adjustmentAdvice?.label || "待确认" }}</strong>
          </div>
        </div>
      </div>

      <div class="choice-grid">
        <article>
          <strong>推荐理由</strong>
          <p>{{ firstChoice.recommendationReason || "待补充推荐理由" }}</p>
        </article>
        <article>
          <strong>风险摘要</strong>
          <p>{{ firstChoice.riskSummary || "待补充风险说明" }}</p>
        </article>
        <article>
          <strong>城市路径</strong>
          <p>{{ firstChoice.cityPathNote || "待补充城市-专业-就业路径说明" }}</p>
        </article>
        <article>
          <strong>调剂建议</strong>
          <p>{{ firstChoice.adjustmentAdvice?.detail || "待确认正式填报时的调剂边界。" }}</p>
        </article>
      </div>
    </article>

    <div class="bucket-table-stack">
      <section
        v-for="bucket in bucketDefinitions"
        :key="bucket.key"
        class="bucket-table-block"
      >
        <header class="section-head compact">
          <div>
            <strong>{{ bucket.title }}</strong>
            <span>{{ bucket.description }}</span>
          </div>
          <el-tag :type="bucket.tagType">
            {{ recommendationBuckets[bucket.key].length }} 个专业组
          </el-tag>
        </header>

        <div
          v-if="recommendationBuckets[bucket.key].length"
          class="recommendation-card-list"
        >
          <article
            v-for="(row, index) in recommendationBuckets[bucket.key]"
            :key="`${row.institutionName}-${row.majorName}-${row.planGroupCode}-${index}`"
            class="recommendation-card"
          >
            <header class="recommendation-card-head">
              <div>
                <small>{{ row.displayTierLabel || row.bucketLabel || bucket.shortTitle || `第 ${index + 1} 项` }}</small>
                <h3>{{ row.institutionName }}</h3>
                <p>{{ row.cityText || row.city || row.province || "待补充城市" }}</p>
              </div>
              <div class="recommendation-tags">
                <el-tag
                  v-if="isFirstChoiceRow(row, firstChoice)"
                  type="success"
                  size="small"
                >
                  第一志愿
                </el-tag>
                <el-tag :type="riskTagType(row.riskLevel)" size="small">
                  {{ row.riskLabel || "待复核" }}
                </el-tag>
              </div>
            </header>

            <div class="recommendation-major">
              <strong>{{ row.majorName }}</strong>
              <span>{{ row.planGroupCode || row.batchCode || "待补充专业组代码" }}</span>
            </div>

            <dl class="recommendation-metrics">
              <div>
                <dt>最低分</dt>
                <dd>{{ formatScore(row.minScore) }}</dd>
              </div>
              <div>
                <dt>最低位次</dt>
                <dd>{{ formatRank(row.minRank) }}</dd>
              </div>
              <div>
                <dt>位次差</dt>
                <dd>{{ formatRankGap(row.rankGap) }}</dd>
              </div>
              <div>
                <dt>分差</dt>
                <dd>{{ formatGap(row.scoreGap) }}</dd>
              </div>
            </dl>

            <div class="recommendation-reason">
              <strong>推荐理由</strong>
              <p>{{ row.recommendationReason || "待补充推荐理由" }}</p>
              <span>{{ row.riskSummary || "待补充风险摘要" }}</span>
            </div>
          </article>
        </div>

        <div v-else class="table-empty">
          当前版本暂未生成该梯度的推荐项。
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.formal-report-block {
  margin-bottom: 20px;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: #ffffff;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-head.compact {
  margin-bottom: 12px;
}

.section-head strong,
.section-head span {
  display: block;
}

.section-head span {
  margin-top: 4px;
  color: var(--app-text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.bucket-summary-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.bucket-stat-card {
  padding: 14px 16px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.bucket-stat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.bucket-stat-card strong {
  display: block;
}

.bucket-stat-card p {
  margin: 0 0 10px;
  line-height: 1.7;
}

.bucket-stat-card span {
  color: var(--app-text-secondary);
  font-size: 12px;
}

.first-choice-card {
  margin: 18px 0;
  padding: 18px;
  border-radius: 8px;
  background: #fbfcf8;
  border: 1px solid rgba(15, 118, 110, 0.2);
}

.first-choice-main {
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  margin-bottom: 16px;
}

.first-choice-main h3 {
  margin: 0 0 6px;
  font-size: 22px;
}

.first-choice-main p,
.first-choice-main span {
  margin: 0;
  color: var(--app-text-secondary);
}

.choice-metrics,
.choice-grid {
  display: grid;
  gap: 12px;
}

.choice-metrics {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.choice-metrics div,
.choice-grid article {
  padding: 12px 14px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.choice-metrics small,
.choice-grid strong {
  display: block;
  color: var(--app-text-secondary);
}

.choice-metrics strong {
  display: block;
  margin-top: 6px;
  font-size: 16px;
}

.choice-grid {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.choice-grid p {
  margin: 8px 0 0;
  line-height: 1.7;
}

.bucket-table-stack {
  display: grid;
  gap: 14px;
}

.bucket-table-block {
  padding: 14px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.recommendation-card-list {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
}

.recommendation-card {
  display: grid;
  gap: 12px;
  min-width: 0;
  padding: 15px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: #f8fafc;
}

.recommendation-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.recommendation-card-head div {
  min-width: 0;
}

.recommendation-card-head small {
  display: block;
  color: #0f766e;
  font-size: 12px;
  font-weight: 800;
}

.recommendation-card-head h3 {
  margin: 5px 0 4px;
  color: #111827;
  font-size: 17px;
  line-height: 1.35;
}

.recommendation-card-head p,
.recommendation-major span,
.recommendation-reason span {
  color: var(--app-text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.recommendation-card-head p,
.recommendation-reason p {
  margin: 0;
}

.recommendation-tags {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 6px;
  flex: 0 0 auto;
}

.recommendation-major {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 6px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.06);
}

.recommendation-major strong {
  color: #111827;
  line-height: 1.45;
}

.recommendation-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
}

.recommendation-metrics div {
  min-width: 0;
  padding: 9px 10px;
  border-radius: 6px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.06);
}

.recommendation-metrics dt {
  color: var(--app-text-secondary);
  font-size: 12px;
}

.recommendation-metrics dd {
  margin: 4px 0 0;
  color: #111827;
  font-weight: 800;
  word-break: break-word;
}

.recommendation-reason {
  display: grid;
  gap: 5px;
}

.recommendation-reason strong {
  color: #475467;
  font-size: 13px;
}

.recommendation-reason p {
  color: #334155;
  line-height: 1.72;
}

.recommendation-reason span {
  display: block;
  padding-top: 4px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
}

.recommendation-card :deep(.el-tag) {
  max-width: 100%;
}

.recommendation-card :deep(.el-tag__content) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-stack small {
  font-weight: 700;
}

.table-empty {
  padding: 18px;
  text-align: center;
  color: var(--app-text-secondary);
  border: 1px dashed rgba(66, 133, 244, 0.2);
  border-radius: 8px;
  background: #ffffff;
}

@media (max-width: 1199px) {
  .first-choice-main {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .section-head,
  .bucket-stat-head,
  .recommendation-card-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .choice-metrics {
    grid-template-columns: 1fr;
  }

  .recommendation-card-list,
  .recommendation-metrics {
    grid-template-columns: 1fr;
  }

  .recommendation-tags {
    justify-content: flex-start;
  }
}
</style>
