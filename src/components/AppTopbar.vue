<script setup>
defineEmits(["toggle-menu"]);
</script>

<template>
  <header class="topbar">
    <div class="topbar-left">
      <el-button class="topbar-menu" text @click="$emit('toggle-menu')">菜单</el-button>
      <div>
        <strong>志愿规划工作台</strong>
        <span>2026 高考季咨询中心后台</span>
      </div>
    </div>

    <div class="topbar-right">
      <span class="status-chip">今日咨询高峰 18:00-21:00</span>
      <div class="user-panel">
        <div class="user-avatar">顾</div>
        <div>
          <strong>顾问老师</strong>
          <span>高级咨询师</span>
        </div>
      </div>
    </div>
  </header>
</template>
