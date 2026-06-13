import provinceSupportDefinition from "../../shared/province_support.json";

export const LAST_VERIFIED_DATE = provinceSupportDefinition.lastVerifiedDate || "";
export const FORMAL_SUPPORTED_PROVINCES = provinceSupportDefinition.formalSupportedProvinces || [];
export const PROVINCE_SUPPORT_CATALOG = provinceSupportDefinition.provinceCatalog || {};

export function buildProvinceSupportOptions() {
  return Object.entries(PROVINCE_SUPPORT_CATALOG)
    .map(([province, config]) => {
      const isFormal = FORMAL_SUPPORTED_PROVINCES.includes(province);
      return {
        value: province,
        label: province,
        status: config.status || "",
        statusLabel: config.statusLabel || "",
        description: config.description || "",
        disabled: !isFormal
      };
    })
    .sort((left, right) => Number(left.disabled) - Number(right.disabled) || left.value.localeCompare(right.value, "zh-CN"));
}

export function buildProvinceSupportSummary() {
  const options = buildProvinceSupportOptions();
  return {
    lastVerifiedDate: LAST_VERIFIED_DATE,
    formalSupportedProvinces: FORMAL_SUPPORTED_PROVINCES,
    formalSupportedLabel: FORMAL_SUPPORTED_PROVINCES.join(" / ") || "待补充",
    pendingProvinces: options.filter((item) => item.disabled).map((item) => item.value),
    options,
    notice: FORMAL_SUPPORTED_PROVINCES.length
      ? `当前正式支持省份仅限 ${FORMAL_SUPPORTED_PROVINCES.join(" / ")}。`
      : "当前尚未明确正式支持省份。"
  };
}
