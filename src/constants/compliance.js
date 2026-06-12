import complianceDefinition from "../../shared/compliance.json";

export const COMPLIANCE_DISCLAIMER = complianceDefinition.disclaimer || "";
export const INTERFACE_BOUNDARY_NOTE = complianceDefinition.interfaceBoundaryNote || "";
export const INTAKE_DISCLAIMER = complianceDefinition.intakeDisclaimer || COMPLIANCE_DISCLAIMER;
export const PORTRAIT_DISCLAIMER = complianceDefinition.portraitDisclaimer || "";
export const COMPLIANCE_COPY_RULES = complianceDefinition.copyRules || [];
export const PROHIBITED_PROMISE_PHRASES = complianceDefinition.prohibitedPromisePhrases || [];

function normalizeForPhraseMatch(value) {
  return String(value || "").replace(/\s+/g, "").toLowerCase();
}

export function findProhibitedPromisePhrases(...values) {
  const haystack = normalizeForPhraseMatch(values.filter(Boolean).join(" "));
  const hits = [];
  PROHIBITED_PROMISE_PHRASES.forEach((phrase) => {
    if (!phrase) {
      return;
    }
    if (haystack.includes(normalizeForPhraseMatch(phrase)) && !hits.includes(phrase)) {
      hits.push(phrase);
    }
  });
  return hits;
}
