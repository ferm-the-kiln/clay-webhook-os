// ─── Sequence Lab Templates & Types ───

export interface SequenceLabTemplate {
  id: string;
  name: string;
  description: string;
  sequenceType: "cold" | "linkedin-first" | "warm-intro";
  data: Record<string, unknown>;
}

export interface SequenceLabRun {
  id: string;
  templateId: string | null;
  model: string;
  variantId: string | null;
  data: Record<string, unknown>;
  instructions: string;
  result: Record<string, unknown>;
  durationMs: number;
  timestamp: number;
}

export const SEQUENCE_TYPES = ["cold", "linkedin-first", "warm-intro"] as const;
export type SequenceType = (typeof SEQUENCE_TYPES)[number];

export const SEQUENCE_TYPE_COLORS: Record<SequenceType, string> = {
  cold: "bg-blue-500/15 text-blue-400",
  "linkedin-first": "bg-purple-500/15 text-purple-400",
  "warm-intro": "bg-amber-500/15 text-amber-400",
};

export const SEQUENCE_LAB_TEMPLATES: SequenceLabTemplate[] = [
  {
    id: "cold-outbound-saas",
    name: "Cold Outbound — SaaS",
    description: "5-touch cold sequence with email + LinkedIn + phone",
    sequenceType: "cold",
    data: {
      first_name: "Marcus",
      last_name: "Rivera",
      title: "VP of Engineering",
      company_name: "Datadog",
      industry: "Observability / SaaS",
      signal_type: "expansion",
      signal_detail:
        "Opening new Austin office, hiring 80+ engineers. Posted 12 video-related ML roles in the last 30 days.",
      sequence_type: "cold",
      client_slug: "twelve-labs",
    },
  },
  {
    id: "cold-outbound-fintech",
    name: "Cold Outbound — Fintech",
    description: "Cold sequence targeting fintech buyer after funding",
    sequenceType: "cold",
    data: {
      first_name: "Priya",
      last_name: "Sharma",
      title: "CTO",
      company_name: "Plaid",
      industry: "Fintech / APIs",
      signal_type: "funding",
      signal_detail:
        "Series D — $425M at $13.4B valuation. Expanding video KYC and identity verification platform.",
      sequence_type: "cold",
      client_slug: "twelve-labs",
    },
  },
  {
    id: "linkedin-first-product",
    name: "LinkedIn-First — Product Launch",
    description: "Lead with LinkedIn connection, follow up via email",
    sequenceType: "linkedin-first",
    data: {
      first_name: "Jordan",
      last_name: "Lee",
      title: "Head of Platform",
      company_name: "Loom",
      industry: "Video Communication / SaaS",
      signal_type: "product_launch",
      signal_detail:
        "Launched AI-powered video summarization. Job posts mention multimodal search capabilities.",
      sequence_type: "linkedin-first",
      client_slug: "twelve-labs",
    },
  },
  {
    id: "linkedin-first-leadership",
    name: "LinkedIn-First — New Leader",
    description: "Warm LinkedIn intro to newly appointed exec",
    sequenceType: "linkedin-first",
    data: {
      first_name: "Diana",
      last_name: "Chen",
      title: "VP of Sales",
      company_name: "Synthesia",
      industry: "AI Video / Enterprise",
      signal_type: "leadership",
      signal_detail:
        "Joined from Clarifai as new VP Sales. Previously led enterprise deals for computer vision products.",
      sequence_type: "linkedin-first",
      client_slug: "twelve-labs",
    },
  },
  {
    id: "warm-intro-referral",
    name: "Warm Intro — Referral",
    description: "Referral-based sequence with social proof",
    sequenceType: "warm-intro",
    data: {
      first_name: "Alex",
      last_name: "Petrov",
      title: "Director of Product",
      company_name: "Vimeo",
      industry: "Video Platform / SaaS",
      signal_type: "referral",
      signal_detail:
        "Referred by David Kim (CEO, Notion) after successful pilot. Currently evaluating video AI vendors.",
      sequence_type: "warm-intro",
      referrer_name: "David Kim",
      referrer_company: "Notion",
      client_slug: "twelve-labs",
    },
  },
];

export const STORAGE_KEY = "sequence-lab-history";
export const MAX_HISTORY = 25;
