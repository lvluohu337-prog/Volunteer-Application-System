import reportProductsDefinition from "../../shared/report_products.json";

export const DEFAULT_REPORT_PRODUCT_CODE = String(reportProductsDefinition.defaultProductCode || "399");

export const REPORT_PRODUCT_CONFIG = Object.fromEntries(
  Object.entries(reportProductsDefinition.formalProducts || {}).map(([code, config]) => [
    code,
    {
      label: config.label || "",
      shortLabel: config.shortLabel || config.label || "",
      description: config.description || "",
      targetUser: config.targetUser || "",
      deliveryChannels: Array.isArray(config.deliveryChannels) ? config.deliveryChannels : []
    }
  ])
);

export const SUPPORTED_REPORT_PRODUCT_CODES = Object.keys(REPORT_PRODUCT_CONFIG);

export const PLANNED_REPORT_PRODUCTS = reportProductsDefinition.plannedProducts || {};

export function getReportProductLabel(productCode) {
  return REPORT_PRODUCT_CONFIG[productCode]?.label ?? REPORT_PRODUCT_CONFIG[DEFAULT_REPORT_PRODUCT_CODE].label;
}

export function normalizeReportProductCode(productCode) {
  const normalized = String(productCode || DEFAULT_REPORT_PRODUCT_CODE).trim();
  return SUPPORTED_REPORT_PRODUCT_CODES.includes(normalized) ? normalized : DEFAULT_REPORT_PRODUCT_CODE;
}
