export const SKILL_SAMPLES: Record<string, Record<string, unknown>> = {
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
  "icp-scorer": {
    first_name: "Marcus",
    last_name: "Rivera",
    title: "Head of Data",
    company_name: "Snowflake",
    industry: "Cloud Data / SaaS",
    employee_count: 5000,
    technologies: "Spark, dbt, Airflow",
    signal_type: "job_posting",
    signal_detail: "Hiring 3 ML engineers",
  },
  "angle-selector": {
    first_name: "Emily",
    last_name: "Park",
    title: "CTO",
    company_name: "Figma",
    industry: "Design Tools / SaaS",
    signal_type: "product_launch",
    signal_detail: "Launched AI-powered design assistant",
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
  "objection-handler": {
    objection: "We already use a competitor for this",
    first_name: "Lisa",
    title: "VP Marketing",
    company_name: "HubSpot",
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
  "follow-up": {
    first_name: "Rachel",
    last_name: "Torres",
    title: "Head of Partnerships",
    company_name: "Stripe",
    meeting_summary: "Discussed API integration timeline, interested in Q2 pilot",
    action_items: "Send SOW draft, schedule technical deep-dive",
    client_slug: "twelve-labs",
  },
  "campaign-brief": {
    campaign_name: "Q2 AI Infrastructure Push",
    target_persona: "VP Engineering at Series B+ SaaS companies",
    value_prop: "Reduce video search latency by 90% with multimodal AI",
    channels: "LinkedIn, Email",
    client_slug: "twelve-labs",
  },
  "quality-gate": {
    email_subject: "Quick question about your video pipeline",
    email_body:
      "Hi Sarah, noticed Lattice just closed your Series D — congrats! With the team scaling, curious if video content search has come up as a pain point. We helped Notion cut their search latency by 90%. Worth a 15-min chat?",
    first_name: "Sarah",
    company_name: "Lattice",
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
  "icp-scorer": [
    { name: "first_name", required: true, placeholder: "Marcus", type: "text" },
    { name: "last_name", required: false, placeholder: "Rivera", type: "text" },
    { name: "title", required: true, placeholder: "Head of Data", type: "text" },
    { name: "company_name", required: true, placeholder: "Snowflake", type: "text" },
    { name: "industry", required: false, placeholder: "Cloud Data / SaaS", type: "text" },
    { name: "employee_count", required: false, placeholder: "5000", type: "number" },
    { name: "technologies", required: false, placeholder: "Spark, dbt, Airflow", type: "text" },
    { name: "signal_type", required: false, placeholder: "job_posting", type: "text" },
    { name: "signal_detail", required: false, placeholder: "Hiring 3 ML engineers", type: "text" },
  ],
  "angle-selector": [
    { name: "first_name", required: true, placeholder: "Emily", type: "text" },
    { name: "last_name", required: false, placeholder: "Park", type: "text" },
    { name: "title", required: true, placeholder: "CTO", type: "text" },
    { name: "company_name", required: true, placeholder: "Figma", type: "text" },
    { name: "industry", required: false, placeholder: "Design Tools / SaaS", type: "text" },
    { name: "signal_type", required: false, placeholder: "product_launch", type: "text" },
    { name: "signal_detail", required: false, placeholder: "Launched AI-powered design assistant", type: "text" },
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
  "objection-handler": [
    { name: "objection", required: true, placeholder: "We already use a competitor", type: "textarea" },
    { name: "first_name", required: false, placeholder: "Lisa", type: "text" },
    { name: "title", required: false, placeholder: "VP Marketing", type: "text" },
    { name: "company_name", required: false, placeholder: "HubSpot", type: "text" },
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
  "follow-up": [
    { name: "first_name", required: true, placeholder: "Rachel", type: "text" },
    { name: "last_name", required: false, placeholder: "Torres", type: "text" },
    { name: "title", required: false, placeholder: "Head of Partnerships", type: "text" },
    { name: "company_name", required: true, placeholder: "Stripe", type: "text" },
    { name: "meeting_summary", required: true, placeholder: "Discussed API integration timeline...", type: "textarea" },
    { name: "action_items", required: false, placeholder: "Send SOW draft, schedule deep-dive", type: "textarea" },
    { name: "client_slug", required: false, placeholder: "twelve-labs", type: "text" },
  ],
  "campaign-brief": [
    { name: "campaign_name", required: true, placeholder: "Q2 AI Infrastructure Push", type: "text" },
    { name: "target_persona", required: true, placeholder: "VP Engineering at Series B+ SaaS", type: "text" },
    { name: "value_prop", required: true, placeholder: "Reduce video search latency by 90%", type: "textarea" },
    { name: "channels", required: false, placeholder: "LinkedIn, Email", type: "text" },
    { name: "client_slug", required: false, placeholder: "twelve-labs", type: "text" },
  ],
  "quality-gate": [
    { name: "email_subject", required: true, placeholder: "Quick question about your pipeline", type: "text" },
    { name: "email_body", required: true, placeholder: "Hi Sarah, noticed Lattice just closed...", type: "textarea" },
    { name: "first_name", required: true, placeholder: "Sarah", type: "text" },
    { name: "company_name", required: true, placeholder: "Lattice", type: "text" },
  ],
};
