// ─── Skill Pillars ───
export const SKILL_PILLARS = {
  "Content Generation": [
    "email-gen",
    "sequence-writer",
    "linkedin-note",
    "follow-up",
    "quality-gate",
  ],
  "Strategic Analysis": [
    "account-researcher",
    "meeting-prep",
    "discovery-questions",
    "competitive-response",
    "champion-enabler",
    "campaign-brief",
    "multi-thread-mapper",
  ],
} as const;

export const SKILL_SAMPLES: Record<string, Record<string, unknown>> = {
  // ─── Content Generation ───
  "email-gen": {
    first_name: "Sarah",
    last_name: "Chen",
    title: "VP Engineering",
    company_name: "Lattice",
    industry: "HR Tech / SaaS",
    signal_type: "funding",
    signal_detail: "Series D — $175M led by Tiger Global",
    client_slug: "twelve-labs",
  },
  "sequence-writer": {
    first_name: "Alex",
    last_name: "Nguyen",
    title: "Head of Product",
    company_name: "Figma",
    industry: "Design Tools / SaaS",
    signal_type: "product_launch",
    signal_detail: "Launched AI-powered design assistant",
    sequence_length: 3,
    channel: "email",
    client_slug: "twelve-labs",
  },
  "linkedin-note": {
    first_name: "James",
    last_name: "Okafor",
    title: "Director of Sales",
    company_name: "Gong",
    signal_type: "promotion",
    signal_detail: "Promoted from Senior Manager",
    client_slug: "twelve-labs",
  },
  "follow-up": {
    first_name: "Rachel",
    last_name: "Torres",
    title: "Head of Partnerships",
    company_name: "Stripe",
    meeting_summary: "Discussed API integration timeline, interested in Q2 pilot",
    action_items: "Send SOW draft, schedule technical deep-dive",
    client_slug: "twelve-labs",
  },
  "quality-gate": {
    email_subject: "Quick question about your video pipeline",
    email_body:
      "Hi Sarah, noticed Lattice just closed your Series D — congrats! With the team scaling, curious if video content search has come up as a pain point. We helped Notion cut their search latency by 90%. Worth a 15-min chat?",
    first_name: "Sarah",
    company_name: "Lattice",
  },
  // ─── Strategic Analysis ───
  "account-researcher": {
    company_name: "Notion",
    company_domain: "notion.so",
    industry: "Productivity / SaaS",
    client_slug: "twelve-labs",
  },
  "meeting-prep": {
    first_name: "David",
    last_name: "Kim",
    title: "CEO",
    company_name: "Notion",
    meeting_type: "discovery",
    meeting_notes: "Inbound from website demo request",
    client_slug: "twelve-labs",
  },
  "discovery-questions": {
    first_name: "Maria",
    last_name: "Santos",
    title: "VP Operations",
    company_name: "Datadog",
    industry: "Observability / SaaS",
    meeting_type: "discovery",
    known_pain_points: "Video content search is slow, manual tagging bottleneck",
    client_slug: "twelve-labs",
  },
  "competitive-response": {
    competitor_name: "Clarifai",
    competitor_claim: "Best-in-class video understanding AI with 99% accuracy",
    prospect_company: "Datadog",
    prospect_title: "VP Engineering",
    client_slug: "twelve-labs",
  },
  "champion-enabler": {
    champion_name: "Priya",
    champion_title: "Senior Engineering Manager",
    champion_company: "Notion",
    deal_stage: "evaluation",
    internal_blockers: "CTO wants to build in-house, budget approval needed from CFO",
    client_slug: "twelve-labs",
  },
  "campaign-brief": {
    campaign_name: "Q2 AI Infrastructure Push",
    target_persona: "VP Engineering at Series B+ SaaS companies",
    value_prop: "Reduce video search latency by 90% with multimodal AI",
    channels: "LinkedIn, Email",
    client_slug: "twelve-labs",
  },
  "multi-thread-mapper": {
    company_name: "Notion",
    deal_stage: "evaluation",
    known_contacts: "David Kim (CEO), Priya Sharma (Sr Eng Manager)",
    target_departments: "Engineering, Product, Operations",
    client_slug: "twelve-labs",
  },
};

export const MODELS = ["opus", "sonnet", "haiku"] as const;
export type Model = (typeof MODELS)[number];

export interface SkillFieldMeta {
  name: string;
  required: boolean;
  placeholder: string;
  type: "text" | "textarea" | "number";
}

export const SKILL_FIELDS: Record<string, SkillFieldMeta[]> = {
  // ─── Content Generation ───
  "email-gen": [
    { name: "first_name", required: true, placeholder: "Sarah", type: "text" },
    { name: "last_name", required: false, placeholder: "Chen", type: "text" },
    { name: "title", required: true, placeholder: "VP Engineering", type: "text" },
    { name: "company_name", required: true, placeholder: "Lattice", type: "text" },
    { name: "industry", required: false, placeholder: "HR Tech / SaaS", type: "text" },
    { name: "signal_type", required: false, placeholder: "funding", type: "text" },
    { name: "signal_detail", required: false, placeholder: "Series D — $175M", type: "text" },
    { name: "client_slug", required: false, placeholder: "twelve-labs", type: "text" },
  ],
  "sequence-writer": [
    { name: "first_name", required: true, placeholder: "Alex", type: "text" },
    { name: "last_name", required: false, placeholder: "Nguyen", type: "text" },
    { name: "title", required: true, placeholder: "Head of Product", type: "text" },
    { name: "company_name", required: true, placeholder: "Figma", type: "text" },
    { name: "industry", required: false, placeholder: "Design Tools / SaaS", type: "text" },
    { name: "signal_type", required: false, placeholder: "product_launch", type: "text" },
    { name: "signal_detail", required: false, placeholder: "Launched AI-powered design assistant", type: "text" },
    { name: "sequence_length", required: false, placeholder: "3", type: "number" },
    { name: "channel", required: false, placeholder: "email", type: "text" },
    { name: "client_slug", required: false, placeholder: "twelve-labs", type: "text" },
  ],
  "linkedin-note": [
    { name: "first_name", required: true, placeholder: "James", type: "text" },
    { name: "last_name", required: false, placeholder: "Okafor", type: "text" },
    { name: "title", required: false, placeholder: "Director of Sales", type: "text" },
    { name: "company_name", required: true, placeholder: "Gong", type: "text" },
    { name: "signal_type", required: false, placeholder: "promotion", type: "text" },
    { name: "signal_detail", required: false, placeholder: "Promoted from Senior Manager", type: "text" },
    { name: "client_slug", required: false, placeholder: "twelve-labs", type: "text" },
  ],
  "follow-up": [
    { name: "first_name", required: true, placeholder: "Rachel", type: "text" },
    { name: "last_name", required: false, placeholder: "Torres", type: "text" },
    { name: "title", required: false, placeholder: "Head of Partnerships", type: "text" },
    { name: "company_name", required: true, placeholder: "Stripe", type: "text" },
    { name: "meeting_summary", required: true, placeholder: "Discussed API integration timeline...", type: "textarea" },
    { name: "action_items", required: false, placeholder: "Send SOW draft, schedule deep-dive", type: "textarea" },
    { name: "client_slug", required: false, placeholder: "twelve-labs", type: "text" },
  ],
  "quality-gate": [
    { name: "email_subject", required: true, placeholder: "Quick question about your pipeline", type: "text" },
    { name: "email_body", required: true, placeholder: "Hi Sarah, noticed Lattice just closed...", type: "textarea" },
    { name: "first_name", required: true, placeholder: "Sarah", type: "text" },
    { name: "company_name", required: true, placeholder: "Lattice", type: "text" },
  ],
  "find-email": [
    { name: "first_name", required: true, placeholder: "Sarah", type: "text" },
    { name: "last_name", required: true, placeholder: "Chen", type: "text" },
    { name: "company_domain", required: true, placeholder: "lattice.com", type: "text" },
  ],
  // ─── Strategic Analysis ───
  "account-researcher": [
    { name: "company_name", required: true, placeholder: "Notion", type: "text" },
    { name: "company_domain", required: false, placeholder: "notion.so", type: "text" },
    { name: "industry", required: false, placeholder: "Productivity / SaaS", type: "text" },
    { name: "client_slug", required: false, placeholder: "twelve-labs", type: "text" },
  ],
  "meeting-prep": [
    { name: "first_name", required: true, placeholder: "David", type: "text" },
    { name: "last_name", required: false, placeholder: "Kim", type: "text" },
    { name: "title", required: false, placeholder: "CEO", type: "text" },
    { name: "company_name", required: true, placeholder: "Notion", type: "text" },
    { name: "meeting_type", required: false, placeholder: "discovery", type: "text" },
    { name: "meeting_notes", required: false, placeholder: "Inbound from website demo request", type: "textarea" },
    { name: "client_slug", required: false, placeholder: "twelve-labs", type: "text" },
  ],
  "discovery-questions": [
    { name: "first_name", required: true, placeholder: "Maria", type: "text" },
    { name: "last_name", required: false, placeholder: "Santos", type: "text" },
    { name: "title", required: true, placeholder: "VP Operations", type: "text" },
    { name: "company_name", required: true, placeholder: "Datadog", type: "text" },
    { name: "industry", required: false, placeholder: "Observability / SaaS", type: "text" },
    { name: "meeting_type", required: false, placeholder: "discovery", type: "text" },
    { name: "known_pain_points", required: false, placeholder: "Video content search is slow, manual tagging bottleneck", type: "textarea" },
    { name: "client_slug", required: false, placeholder: "twelve-labs", type: "text" },
  ],
  "competitive-response": [
    { name: "competitor_name", required: true, placeholder: "Clarifai", type: "text" },
    { name: "competitor_claim", required: true, placeholder: "Best-in-class video understanding AI with 99% accuracy", type: "textarea" },
    { name: "prospect_company", required: false, placeholder: "Datadog", type: "text" },
    { name: "prospect_title", required: false, placeholder: "VP Engineering", type: "text" },
    { name: "client_slug", required: false, placeholder: "twelve-labs", type: "text" },
  ],
  "champion-enabler": [
    { name: "champion_name", required: true, placeholder: "Priya", type: "text" },
    { name: "champion_title", required: true, placeholder: "Senior Engineering Manager", type: "text" },
    { name: "champion_company", required: true, placeholder: "Notion", type: "text" },
    { name: "deal_stage", required: false, placeholder: "evaluation", type: "text" },
    { name: "internal_blockers", required: false, placeholder: "CTO wants to build in-house, budget approval needed", type: "textarea" },
    { name: "client_slug", required: false, placeholder: "twelve-labs", type: "text" },
  ],
  "campaign-brief": [
    { name: "campaign_name", required: true, placeholder: "Q2 AI Infrastructure Push", type: "text" },
    { name: "target_persona", required: true, placeholder: "VP Engineering at Series B+ SaaS", type: "text" },
    { name: "value_prop", required: true, placeholder: "Reduce video search latency by 90%", type: "textarea" },
    { name: "channels", required: false, placeholder: "LinkedIn, Email", type: "text" },
    { name: "client_slug", required: false, placeholder: "twelve-labs", type: "text" },
  ],
  "multi-thread-mapper": [
    { name: "company_name", required: true, placeholder: "Notion", type: "text" },
    { name: "deal_stage", required: false, placeholder: "evaluation", type: "text" },
    { name: "known_contacts", required: false, placeholder: "David Kim (CEO), Priya Sharma (Sr Eng Manager)", type: "textarea" },
    { name: "target_departments", required: false, placeholder: "Engineering, Product, Operations", type: "text" },
    { name: "client_slug", required: false, placeholder: "twelve-labs", type: "text" },
  ],
};
