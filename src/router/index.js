import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", redirect: { name: "dashboard" } },
  { path: "/dashboard", name: "dashboard", component: () => import("../pages/DashboardPage.vue") },
  { path: "/students", name: "students", component: () => import("../pages/StudentsPage.vue") },
  { path: "/students/:studentId", name: "student-detail", component: () => import("../pages/StudentDetailPage.vue") },
  { path: "/intake", name: "intake", component: () => import("../pages/IntakePage.vue") },
  { path: "/analysis", name: "analysis", component: () => import("../pages/AnalysisPage.vue") },
  { path: "/majors", name: "majors", component: () => import("../pages/MajorsPage.vue") },
  { path: "/plan", name: "plan", component: () => import("../pages/PlanPage.vue") },
  { path: "/reports", name: "reports", component: () => import("../pages/ReportsPage.vue") },
  { path: "/base-data", name: "base-data", component: () => import("../pages/BaseDataPage.vue") },
  { path: "/demo-reports", name: "demo-reports", component: () => import("../pages/DemoReportsPage.vue") },
  { path: "/settings", name: "settings", component: () => import("../pages/SettingsPage.vue") }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  }
});

export default router;
