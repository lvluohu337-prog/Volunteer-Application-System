import process from "node:process";
import { Lunar, Solar } from "lunar-javascript";

const STEM_ELEMENT_MAP = {
  甲: "木",
  乙: "木",
  丙: "火",
  丁: "火",
  戊: "土",
  己: "土",
  庚: "金",
  辛: "金",
  壬: "水",
  癸: "水",
};

const BRANCH_ELEMENT_MAP = {
  子: "水",
  丑: "土",
  寅: "木",
  卯: "木",
  辰: "土",
  巳: "火",
  午: "火",
  未: "土",
  申: "金",
  酉: "金",
  戌: "土",
  亥: "水",
};

function readInput() {
  const raw = process.argv[2];
  if (!raw) {
    throw new Error("missing-json-arg");
  }
  return JSON.parse(raw);
}

function parseDateParts(dateText) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateText ?? "");
  if (!match) {
    throw new Error("invalid-birthday");
  }
  return {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
  };
}

function parseTimeParts(timeText) {
  if (!timeText) {
    return null;
  }
  const match = /^(\d{2}):(\d{2})$/.exec(timeText);
  if (!match) {
    throw new Error("invalid-birth-time");
  }
  const hour = Number(match[1]);
  const minute = Number(match[2]);
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) {
    throw new Error("invalid-birth-time");
  }
  return { hour, minute };
}

function shiftMinutes(date, minutes) {
  return new Date(date.getTime() + minutes * 60 * 1000);
}

function formatDate(date) {
  return [
    String(date.getUTCFullYear()).padStart(4, "0"),
    String(date.getUTCMonth() + 1).padStart(2, "0"),
    String(date.getUTCDate()).padStart(2, "0"),
  ].join("-");
}

function formatTime(date) {
  return [
    String(date.getUTCHours()).padStart(2, "0"),
    String(date.getUTCMinutes()).padStart(2, "0"),
  ].join(":");
}

function isLateZiHour(date) {
  const hour = date.getUTCHours();
  return hour === 23;
}

function buildSolarDate(input) {
  const dateParts = parseDateParts(input.birthday);
  const timeParts = parseTimeParts(input.birthTime);
  const hour = timeParts?.hour ?? 12;
  const minute = timeParts?.minute ?? 0;
  const beijingDate = new Date(Date.UTC(dateParts.year, dateParts.month - 1, dateParts.day, hour, minute, 0));
  return { beijingDate, timeParts };
}

function applyTrueSolarTime(beijingDate, longitude, notes) {
  if (longitude == null || longitude === "") {
    return {
      solarDate: beijingDate,
      trueSolarTime: null,
    };
  }
  const offsetMinutes = Math.round((Number(longitude) - 120) * 4);
  if (offsetMinutes !== 0) {
    notes.push(`true-solar-time:${offsetMinutes}`);
  }
  const solarDate = shiftMinutes(beijingDate, offsetMinutes);
  return {
    solarDate,
    trueSolarTime: formatTime(solarDate),
  };
}

function collectWuxing(pillars) {
  const counts = { 木: 0, 火: 0, 土: 0, 金: 0, 水: 0 };
  for (const pillar of Object.values(pillars)) {
    if (!pillar || pillar.length < 2) {
      continue;
    }
    const stem = pillar[0];
    const branch = pillar[1];
    if (STEM_ELEMENT_MAP[stem]) {
      counts[STEM_ELEMENT_MAP[stem]] += 1;
    }
    if (BRANCH_ELEMENT_MAP[branch]) {
      counts[BRANCH_ELEMENT_MAP[branch]] += 1;
    }
  }
  const ranked = Object.entries(counts)
    .filter(([, count]) => count > 0)
    .sort((left, right) => {
      if (right[1] !== left[1]) {
        return right[1] - left[1];
      }
      return left[0].localeCompare(right[0], "zh-Hans-CN");
    })
    .map(([element]) => element);
  return {
    counts,
    dominant: ranked[0] ?? null,
    secondary: ranked[1] ?? null,
  };
}

function buildPayload(input) {
  const notes = [];
  const { beijingDate, timeParts } = buildSolarDate(input);
  const { solarDate, trueSolarTime } = applyTrueSolarTime(beijingDate, input.longitude, notes);
  const normalizedBusinessDate = timeParts && isLateZiHour(solarDate) ? shiftMinutes(solarDate, 60) : solarDate;

  if (timeParts && formatDate(normalizedBusinessDate) !== formatDate(beijingDate)) {
    notes.push("late-zi-hour-next-day");
  }

  const solar = Solar.fromYmdHms(
    solarDate.getUTCFullYear(),
    solarDate.getUTCMonth() + 1,
    solarDate.getUTCDate(),
    solarDate.getUTCHours(),
    solarDate.getUTCMinutes(),
    0,
  );
  const lunar = Lunar.fromSolar(solar);
  const pillars = {
    year: lunar.getYearInGanZhiExact(),
    month: lunar.getMonthInGanZhi(),
    day: lunar.getDayInGanZhiExact(),
    hour: timeParts ? lunar.getTimeInGanZhi() : null,
  };

  return {
    engineVersion: "bazi_lunar_v1",
    normalizedBirthDate: formatDate(normalizedBusinessDate),
    normalizedBirthTime: timeParts ? formatTime(solarDate) : null,
    trueSolarTime,
    longitude: input.longitude ?? null,
    pillars,
    wuxing: collectWuxing(pillars),
    normalizationNotes: [...new Set(notes)],
  };
}

function main() {
  const input = readInput();
  process.stdout.write(JSON.stringify(buildPayload(input)));
}

main();
