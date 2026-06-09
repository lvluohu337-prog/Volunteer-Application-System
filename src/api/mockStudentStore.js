import { studentRows } from "../data/mock.js";

const STORAGE_KEY = "gaokao-planning-students";

function pad(value) {
  return String(value).padStart(2, "0");
}

function formatDateTime(date = new Date()) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function calculateScore(student) {
  const fields = ["chinese", "math", "english", "physics", "chemistry", "biology"];
  return fields.reduce((total, key) => total + Number(student[key] || 0), 0);
}

function seedStudents() {
  return studentRows.map((row, index) => ({
    id: row.id ?? index + 1,
    name: row.name,
    province: row.province,
    year: Number(row.year),
    subjects: row.subjects,
    chinese: 0,
    math: 0,
    english: 0,
    physics: 0,
    chemistry: 0,
    biology: 0,
    cities: "",
    budget: "",
    majorPreference: "",
    logic: 3,
    expression: 3,
    stability: 3,
    graduate: "暂不考虑",
    status: row.status,
    statusVariant: row.statusVariant,
    updatedAt: row.updatedAt,
    score: row.score
  }));
}

function getStorage() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage;
}

export function loadStudents() {
  const storage = getStorage();
  if (!storage) {
    return seedStudents();
  }

  const stored = storage.getItem(STORAGE_KEY);
  if (!stored) {
    const seeded = seedStudents();
    storage.setItem(STORAGE_KEY, JSON.stringify(seeded));
    return seeded;
  }

  try {
    const parsed = JSON.parse(stored);
    return Array.isArray(parsed) ? parsed : seedStudents();
  } catch {
    const seeded = seedStudents();
    storage.setItem(STORAGE_KEY, JSON.stringify(seeded));
    return seeded;
  }
}

export function saveStudents(students) {
  const storage = getStorage();
  if (!storage) {
    return;
  }

  storage.setItem(STORAGE_KEY, JSON.stringify(students));
}

export function upsertStudent(form, studentId) {
  const students = loadStudents();
  const existing = studentId ? students.find((item) => item.id === Number(studentId)) : null;

  const nextStudent = {
    id: existing?.id ?? Date.now(),
    name: form.name?.trim() ?? "",
    province: form.province ?? "",
    year: Number(form.year || 2026),
    subjects: form.subjects ?? "",
    chinese: Number(form.chinese || 0),
    math: Number(form.math || 0),
    english: Number(form.english || 0),
    physics: Number(form.physics || 0),
    chemistry: Number(form.chemistry || 0),
    biology: Number(form.biology || 0),
    cities: form.cities ?? "",
    budget: form.budget ?? "",
    majorPreference: form.majorPreference ?? "",
    logic: Number(form.logic || 3),
    expression: Number(form.expression || 3),
    stability: Number(form.stability || 3),
    graduate: form.graduate ?? "暂不考虑",
    status: "已完成基础信息",
    statusVariant: "primary",
    updatedAt: formatDateTime(),
    score: calculateScore(form)
  };

  const nextStudents = existing
    ? students.map((item) => (item.id === existing.id ? nextStudent : item))
    : [nextStudent, ...students];

  saveStudents(nextStudents);
  return nextStudent;
}

export function getStudentById(studentId) {
  return loadStudents().find((item) => item.id === Number(studentId)) ?? null;
}

export function mapStudentRow(student) {
  return {
    id: student.id,
    name: student.name,
    province: student.province,
    year: String(student.year),
    subjects: student.subjects,
    score: student.score ?? calculateScore(student),
    status: student.status ?? "已完成基础信息",
    statusVariant: student.statusVariant ?? "primary",
    updatedAt: student.updatedAt ?? formatDateTime()
  };
}

export function filterStudents(students, filters = {}) {
  return students.filter((student) => {
    const matchKeyword = !filters.keyword || student.name.includes(filters.keyword.trim());
    const matchProvince = !filters.province || filters.province === "全部省份" || student.province === filters.province;
    const matchStatus = !filters.status || filters.status === "全部状态" || student.status === filters.status;
    const matchDate = !filters.date || (student.updatedAt ?? "").startsWith(filters.date);

    return matchKeyword && matchProvince && matchStatus && matchDate;
  });
}

export function getStudentFilterOptions(students) {
  const provinceSet = new Set(students.map((item) => item.province).filter(Boolean));
  const statusSet = new Set(students.map((item) => item.status).filter(Boolean));

  return {
    provinces: ["全部省份", ...provinceSet],
    statuses: ["全部状态", ...statusSet]
  };
}
