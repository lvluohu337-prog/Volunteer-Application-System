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
</script>

<template>
  <section class="formal-report-block">
    <header class="section-head">
      <div>
        <strong>正式院校专业推荐表</strong>
        <span>核心交付以真实院校、专业、专业组代码、最低分和最低位次为主，画像信息仅负责解释，不参与硬录取判断。</span>
      </div>
      <el-tag type="primary">
        共 {{ recommendationTable.length }} 条推荐
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
        <span>{{ recommendationBuckets[bucket.key].length }} 条</span>
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
            {{ recommendationBuckets[bucket.key].length }} 条
          </el-tag>
        </header>

        <el-table
          v-if="recommendationBuckets[bucket.key].length"
          :data="recommendationBuckets[bucket.key]"
          stripe
          class="report-table"
        >
          <el-table-column label="院校 / 城市" min-width="190">
            <template #default="{ row }">
              <div class="cell-stack">
                <strong>{{ row.institutionName }}</strong>
                <span>{{ row.cityText || row.city || row.province || "待补充城市" }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="专业 / 专业组" min-width="210">
            <template #default="{ row }">
              <div class="cell-stack">
                <strong>{{ row.majorName }}</strong>
                <span>{{ row.planGroupCode || row.batchCode || "待补充代码" }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="最低分 / 位次" min-width="150">
            <template #default="{ row }">
              <div class="cell-stack">
                <strong>{{ formatScore(row.minScore) }}</strong>
                <span>{{ formatRank(row.minRank) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="位次差 / 分差" min-width="150">
            <template #default="{ row }">
              <div class="cell-stack">
                <strong>{{ formatRankGap(row.rankGap) }}</strong>
                <span>{{ formatGap(row.scoreGap) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="风险等级" min-width="110">
            <template #default="{ row }">
              <el-tag :type="riskTagType(row.riskLevel)">
                {{ row.riskLabel || "待复核" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="推荐理由与提示" min-width="340">
            <template #default="{ row }">
              <div class="reason-stack">
                <p>{{ row.recommendationReason || "待补充推荐理由" }}</p>
                <span>{{ row.riskSummary || "待补充风险摘要" }}</span>
              </div>
            </template>
          </el-table-column>
        </el-table>

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
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(66, 133, 244, 0.12);
  background: linear-gradient(180deg, rgba(66, 133, 244, 0.08), rgba(66, 133, 244, 0.03));
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
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(66, 133, 244, 0.1);
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
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(66, 133, 244, 0.14);
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
  border-radius: 14px;
  background: rgba(66, 133, 244, 0.06);
  border: 1px solid rgba(66, 133, 244, 0.1);
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
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(66, 133, 244, 0.1);
}

.report-table :deep(.el-table__cell) {
  vertical-align: top;
}

.cell-stack,
.reason-stack {
  display: grid;
  gap: 4px;
}

.cell-stack strong,
.reason-stack p {
  margin: 0;
}

.cell-stack span,
.reason-stack span {
  color: var(--app-text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.table-empty {
  padding: 18px;
  text-align: center;
  color: var(--app-text-secondary);
  border: 1px dashed rgba(66, 133, 244, 0.2);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.74);
}

@media (max-width: 1199px) {
  .first-choice-main {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .section-head,
  .bucket-stat-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .choice-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
