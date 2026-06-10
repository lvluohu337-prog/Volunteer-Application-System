<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppShell from "./components/AppShell.vue";

const navigationItems = [
  { key: "dashboard", label: "工作台", short: "DB" },
  { key: "students", label: "学生管理", short: "ST" },
  { key: "intake", label: "学生录入", short: "FM" },
  { key: "reports", label: "报告管理", short: "RP" }
];

const dialogVisible = ref(false);
const dialogTitle = ref("操作确认");
const dialogMessage = ref("请确认是否继续执行该操作。");
const route = useRoute();
const router = useRouter();

const currentPage = computed(() => {
  if (typeof route.name === "string") {
    return route.name;
  }

  return "dashboard";
});

function navigate(page) {
  router.push({ name: page });
}

function openDialog(payload) {
  if (typeof payload === "string") {
    dialogTitle.value = "操作确认";
    dialogMessage.value = payload;
  } else {
    dialogTitle.value = payload.title ?? "操作确认";
    dialogMessage.value = payload.message ?? "请确认是否继续执行该操作。";
  }
  dialogVisible.value = true;
}
</script>

<template>
  <AppShell
    :current-page="currentPage"
    :navigation-items="navigationItems"
    @navigate="navigate"
  >
    <RouterView v-slot="{ Component }">
      <component
        :is="Component"
        @navigate="navigate"
        @open-dialog="openDialog"
      />
    </RouterView>
  </AppShell>

  <el-dialog
    v-model="dialogVisible"
    :title="dialogTitle"
    width="420px"
    align-center
  >
    <p class="dialog-copy">{{ dialogMessage }}</p>

    <template #footer>
      <div class="dialog-actions">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="dialogVisible = false">确认</el-button>
      </div>
    </template>
  </el-dialog>
</template>
