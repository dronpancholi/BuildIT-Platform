export interface VariableDefinition {
  name: string;
  label: string;
  category: string;
  sample: string;
}

export const VARIABLE_DEFINITIONS: VariableDefinition[] = [
  { name: "customer_name", label: "Customer Name", category: "customer", sample: "Acme Corp" },
  { name: "campaign_name", label: "Campaign Name", category: "campaign", sample: "Q1 Outreach" },
  { name: "prospect_name", label: "Prospect Name", category: "prospect", sample: "John Smith" },
  { name: "website", label: "Website", category: "prospect", sample: "example.com" },
  { name: "industry", label: "Industry", category: "prospect", sample: "Technology" },
  { name: "first_name", label: "First Name", category: "prospect", sample: "John" },
  { name: "last_name", label: "Last Name", category: "prospect", sample: "Smith" },
  { name: "domain", label: "Domain", category: "prospect", sample: "example.com" },
  { name: "sender_name", label: "Sender Name", category: "sender", sample: "Jane Doe" },
  { name: "previous_subject", label: "Previous Subject", category: "email", sample: "Re: Your inquiry" },
  { name: "report_type", label: "Report Type", category: "report", sample: "Monthly SEO" },
  { name: "period", label: "Period", category: "report", sample: "January 2026" },
  { name: "active_campaigns", label: "Active Campaigns", category: "report", sample: "12" },
  { name: "links_acquired", label: "Links Acquired", category: "report", sample: "45" },
  { name: "response_rate", label: "Response Rate", category: "report", sample: "24" },
];

const VARIABLE_REGEX = /\{\{(\w+)\}\}/g;

export function parseVariables(text: string): string[] {
  const matches = new Set<string>();
  let match;
  while ((match = VARIABLE_REGEX.exec(text)) !== null) {
    matches.add(match[1]);
  }
  return Array.from(matches);
}

export function resolveVariables(
  text: string,
  data: Record<string, string>
): string {
  return text.replace(VARIABLE_REGEX, (match, name: string) => {
    return data[name] !== undefined ? data[name] : match;
  });
}

export interface ValidationResult {
  missing: string[];
  valid: string[];
  unknown: string[];
}

export function validateVariables(
  text: string,
  knownVariables: string[]
): ValidationResult {
  const used = parseVariables(text);
  const knownSet = new Set(knownVariables);
  const allKnown = new Set(VARIABLE_DEFINITIONS.map((v) => v.name));
  const valid: string[] = [];
  const missing: string[] = [];
  const unknown: string[] = [];

  for (const v of used) {
    if (knownSet.has(v) || allKnown.has(v)) {
      valid.push(v);
      if (!knownSet.has(v) && allKnown.has(v)) {
        missing.push(v);
      }
    } else {
      unknown.push(v);
    }
  }

  return { missing, valid, unknown };
}

export function getVariableByCategory(): Record<string, VariableDefinition[]> {
  const grouped: Record<string, VariableDefinition[]> = {};
  for (const v of VARIABLE_DEFINITIONS) {
    if (!grouped[v.category]) grouped[v.category] = [];
    grouped[v.category].push(v);
  }
  return grouped;
}

export function buildVariableData(
  variables: string[],
  overrides?: Record<string, string>
): Record<string, string> {
  const data: Record<string, string> = {};
  for (const v of variables) {
    if (overrides?.[v]) {
      data[v] = overrides[v];
      continue;
    }
    const def = VARIABLE_DEFINITIONS.find((d) => d.name === v);
    data[v] = def?.sample ?? `{{${v}}}`;
  }
  return data;
}
