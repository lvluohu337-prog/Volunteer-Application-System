<script setup>
defineProps({
  noteForm: {
    type: Object,
    required: true
  },
  savingNote: {
    type: Boolean,
    default: false
  },
  complianceNote: {
    type: String,
    default: "禁止使用承诺性表述。"
  },
  advisorNotes: {
    type: Array,
    default: () => []
  },
  generationRecords: {
    type: Array,
    default: () => []
  },
  deliveryRecords: {
    type: Array,
    default: () => []
  },
  reportTitle: {
    type: String,
    default: ""
  },
  downloadingRecordId: {
    type: [Number, String],
    default: null
  },
  formatFileSize: {
    type: Function,
    required: true
  }
});

const emit = defineEmits(["submit-note", "download-record", "update-note-field"]);
</script>

<template>
  <section class="traceability-panel" aria-labelledby="traceability-title">
    <header class="traceability-panel-head">
      <span>报告作业区</span>
      <h2 id="traceability-title">交付留痕与顾问补充</h2>
      <p>以下内容用于顾问复核、文件导出和过程归档，不作为家长阅读正式结论的第一层信息。</p>
    </header>

    <div class="traceability-grid">
    <article class="traceability-card">
      <header class="traceability-head">
        <strong>咨询师补充备注</strong>
        <span>这些内容会作为正式交付前的人工作业留痕。</span>
      </header>
      <div class="note-form">
        <el-input
          :model-value="noteForm.author_name"
          placeholder="咨询师姓名"
          @update:model-value="emit('update-note-field', 'author_name', $event)"
        />
        <el-input
          :model-value="noteForm.note_title"
          placeholder="备注标题，例如：与家长沟通重点"
          @update:model-value="emit('update-note-field', 'note_title', $event)"
        />
        <el-input
          :model-value="noteForm.note_content"
          type="textarea"
          :rows="4"
          placeholder="输入本次需要补充给报告的人工作业说明、特殊提醒或沟通结论。"
          @update:model-value="emit('update-note-field', 'note_content', $event)"
        />
        <div class="note-actions">
          <el-button type="primary" :loading="savingNote" @click="emit('submit-note')">
            保存咨询师备注
          </el-button>
        </div>
      </div>
      <p class="table-note">
        顾问备注同样适用统一合规口径：{{ complianceNote }}
      </p>
      <div v-if="advisorNotes.length" class="trace-list">
        <article
          v-for="note in advisorNotes"
          :key="note.id"
          class="trace-item"
        >
          <strong>{{ note.note_title || "未命名备注" }}</strong>
          <span>{{ note.author_name || "咨询师" }} / {{ note.updated_at }}</span>
          <p>{{ note.note_content }}</p>
        </article>
      </div>
      <p v-else class="table-note">当前还没有咨询师补充备注，适合在人工复核后开始积累。</p>
    </article>

    <article class="traceability-card">
      <header class="traceability-head">
        <strong>报告生成记录</strong>
        <span>每次打开真实报告都会自动记录一条生成留痕。</span>
      </header>
      <div v-if="generationRecords.length" class="trace-list">
        <article
          v-for="record in generationRecords"
          :key="record.id"
          class="trace-item"
        >
          <strong>{{ record.report_title || reportTitle }}</strong>
          <span>
            {{ record.created_at }} / {{ record.generation_mode || "preview" }} / {{ record.generated_by || "system-preview" }}
          </span>
          <p>
            {{ record.summary?.scoreLevel || "待补充分层" }}
            <template v-if="record.summary?.matchedMajors?.length">
              / {{ record.summary.matchedMajors.join("、") }}
            </template>
          </p>
        </article>
      </div>
      <p v-else class="table-note">当前还没有生成记录。</p>
    </article>

    <article class="traceability-card">
      <header class="traceability-head">
        <strong>导出与交付记录</strong>
        <span>优先提供可直接访问的下载入口，并保留生成时间、操作人与文件留痕信息。</span>
      </header>
      <div v-if="deliveryRecords.length" class="trace-list">
        <article
          v-for="record in deliveryRecords"
          :key="record.id"
          class="trace-item"
        >
          <div class="trace-item-head">
            <strong>{{ record.export_format?.toUpperCase() }} / {{ record.report_title || reportTitle }}</strong>
            <el-tag :type="record.artifactExists ? 'success' : 'danger'">
              {{ record.artifactExists ? "文件可下载" : "文件缺失" }}
            </el-tag>
          </div>
          <span>{{ record.created_at }} / {{ record.generated_by || "system-export" }}</span>
          <p>{{ record.artifact_name }}</p>
          <div class="trace-download-row">
            <el-button
              type="primary"
              plain
              size="small"
              :disabled="!record.artifactExists"
              :loading="downloadingRecordId === record.id"
              @click="emit('download-record', record)"
            >
              下载 {{ record.export_format?.toUpperCase() || "文件" }}
            </el-button>
            <span class="table-note">
              {{ record.artifactSizeBytes ? formatFileSize(record.artifactSizeBytes) : "待补充文件大小" }}
            </span>
          </div>
          <p class="table-note">留痕路径：{{ record.artifactPathLabel || record.artifact_path }}</p>
        </article>
      </div>
      <p v-else class="table-note">当前还没有导出记录，正式导出后会自动留痕。</p>
    </article>
    </div>
  </section>
</template>

<style scoped>
.traceability-panel {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid rgba(15, 23, 42, 0.1);
}

.traceability-panel-head {
  margin-bottom: 14px;
}

.traceability-panel-head span {
  color: #667085;
  font-size: 13px;
}

.traceability-panel-head h2 {
  margin: 4px 0 0;
  color: #111827;
  font-size: 20px;
}

.traceability-panel-head p {
  max-width: 760px;
  margin: 8px 0 0;
  color: #667085;
  line-height: 1.7;
}

.traceability-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.traceability-card {
  padding: 18px;
  border-radius: 8px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #f8fafc;
}

.traceability-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 14px;
}

.traceability-head span {
  color: var(--app-text-secondary);
  font-size: 13px;
}

.note-form {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
}

.note-actions {
  display: flex;
  justify-content: flex-end;
}

.trace-list {
  display: grid;
  gap: 10px;
}

.trace-item {
  padding: 12px 14px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.trace-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.trace-download-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.trace-item strong {
  display: block;
}

.trace-item span {
  display: block;
  margin: 6px 0 8px;
  color: var(--app-text-secondary);
  font-size: 12px;
}

.trace-item p {
  margin: 0;
  line-height: 1.7;
}
</style>
