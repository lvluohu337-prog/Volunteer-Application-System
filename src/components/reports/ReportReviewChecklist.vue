<script setup>
defineProps({
  items: {
    type: Array,
    default: () => [
      "招生章程",
      "组内 6 个专业接受度",
      "是否服从调剂",
      "体检/单科/语种/性别限制",
      "当年招生计划变化",
      "最终志愿系统录入顺序"
    ]
  }
});
</script>

<template>
  <section class="report-review-checklist" aria-labelledby="review-checklist-title">
    <header>
      <span>正式提交前</span>
      <h2 id="review-checklist-title">人工复核清单</h2>
      <p>这些事项决定方案能否安全落地，建议在导出或提交志愿前逐项确认。</p>
    </header>

    <ul>
      <li v-for="item in items" :key="item">
        <span aria-hidden="true"></span>
        <strong>{{ item }}</strong>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.report-review-checklist {
  margin: 4px 0 22px;
  padding: 22px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: #ffffff;
}

header span {
  color: #0f766e;
  font-size: 13px;
  font-weight: 700;
}

h2 {
  margin: 4px 0 0;
  color: #111827;
  font-size: 22px;
  font-weight: 750;
}

p {
  max-width: 760px;
  margin: 8px 0 0;
  color: #475467;
  line-height: 1.72;
}

ul {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px 14px;
  margin: 18px 0 0;
  padding: 0;
  list-style: none;
}

li {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 6px;
  background: #f8fafc;
  color: #334155;
}

li span {
  width: 10px;
  height: 10px;
  border: 2px solid #0f766e;
  border-radius: 50%;
  background: #ffffff;
  flex: 0 0 auto;
}

li strong {
  font-size: 14px;
  font-weight: 700;
}

@media (max-width: 1000px) {
  ul {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  ul {
    grid-template-columns: 1fr;
  }
}
</style>
