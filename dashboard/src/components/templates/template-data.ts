import type { WorkflowTemplate } from "@/lib/types";

/**
 * Pre-built workflow templates for sales reps.
 * Each template creates a table with the right columns pre-configured.
 *
 * Column execution modes:
 * - enrichment + tool:"dropleads_email_finder" → Deepline CLI email finding (fast, real data)
 * - enrichment + tool:"apollo_organization_enrich" → Deepline CLI company enrichment
 * - enrichment + tool:"apollo_people_match" → Deepline CLI people matching
 * - ai + ai_prompt → Claude single-turn processing (scoring, synthesis, formatting)
 */
export const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [
  {
    id: "find-emails",
    name: "Find Emails",
    description:
      "Upload a list of prospects with their name and company domain. We'll find their verified work email addresses via Deepline.",
    category: "enrichment",
    icon: "Mail",
    expected_inputs: [
      { name: "first_name", description: "Contact's first name", required: true },
      { name: "last_name", description: "Contact's last name", required: true },
      { name: "domain", description: "Company website domain", required: true },
    ],
    produced_outputs: [
      { name: "email", description: "Verified work email" },
      { name: "confidence", description: "Email confidence score" },
    ],
    columns: [
      {
        name: "Email",
        column_type: "enrichment",
        tool: "dropleads_email_finder",
        params: {
          first_name: "{{first_name}}",
          last_name: "{{last_name}}",
          company_domain: "{{domain}}",
        },
        output_key: "email",
      },
    ],
  },
  {
    id: "research-companies",
    name: "Research Companies",
    description:
      "Get a quick overview of any company — what they do, employee count, industry, and recent news. Uses web research for live data.",
    category: "research",
    icon: "Building2",
    expected_inputs: [
      { name: "domain", description: "Company website domain", required: true },
    ],
    produced_outputs: [
      { name: "summary", description: "What the company does" },
      { name: "employee_count", description: "Estimated employees" },
      { name: "industry", description: "Primary industry" },
    ],
    columns: [
      {
        name: "Company Research",
        column_type: "enrichment",
        tool: "apollo_organization_enrich",
        params: {
          domain: "{{domain}}",
        },
        output_key: "results",
      },
      {
        name: "Company Summary",
        column_type: "ai",
        ai_prompt:
          "Using the Company Research data, return a JSON object with: summary (2-3 sentences about what they do), employee_count (estimated number or range), industry (primary industry), and headquarters (city, state if available). Only use facts from the research — do not guess.",
        ai_model: "sonnet",
      },
    ],
  },
  {
    id: "score-leads",
    name: "Score & Qualify Leads",
    description:
      "Score your prospect list based on company size, industry fit, and other signals. Researches each company first, then scores.",
    category: "scoring",
    icon: "Target",
    expected_inputs: [
      { name: "company_name", description: "Company name", required: true },
      { name: "domain", description: "Company website", required: true },
      { name: "industry", description: "Company industry (optional)", required: false },
    ],
    produced_outputs: [
      { name: "fit_score", description: "0-100 fit score" },
      { name: "reasoning", description: "Why this score" },
      { name: "tier", description: "A, B, or C tier" },
    ],
    columns: [
      {
        name: "Company Intel",
        column_type: "enrichment",
        tool: "apollo_organization_enrich",
        params: {
          domain: "{{domain}}",
        },
        output_key: "results",
      },
      {
        name: "Qualification",
        column_type: "ai",
        ai_prompt:
          'Using the Company Intel research data, analyze {{company_name}} ({{domain}}) as a potential prospect. Return a JSON object with: fit_score (0-100), tier ("A", "B", or "C"), reasoning (1-2 sentences explaining the score based on what you found), and signals (array of positive/negative indicators from the research).',
        ai_model: "sonnet",
      },
    ],
  },
  {
    id: "enrich-contacts",
    name: "Enrich Contacts",
    description:
      "Enrich your contact list with verified emails via Findymail and web-sourced job titles, LinkedIn profiles, and company details.",
    category: "enrichment",
    icon: "Users",
    expected_inputs: [
      { name: "first_name", description: "Contact's first name", required: true },
      { name: "last_name", description: "Contact's last name", required: true },
      { name: "company_name", description: "Company name", required: true },
      { name: "domain", description: "Company domain (optional)", required: false },
    ],
    produced_outputs: [
      { name: "email", description: "Verified work email" },
      { name: "title", description: "Current job title" },
      { name: "linkedin_url", description: "LinkedIn profile URL" },
    ],
    columns: [
      {
        name: "Email",
        column_type: "enrichment",
        tool: "dropleads_email_finder",
        params: {
          first_name: "{{first_name}}",
          last_name: "{{last_name}}",
          company_domain: "{{domain}}",
        },
        output_key: "email",
      },
      {
        name: "Contact Lookup",
        column_type: "enrichment",
        tool: "apollo_people_match",
        params: {
          first_name: "{{first_name}}",
          last_name: "{{last_name}}",
          organization_name: "{{company_name}}",
        },
        output_key: "results",
      },
      {
        name: "Contact Info",
        column_type: "ai",
        ai_prompt:
          "Using the Contact Lookup research data for {{first_name}} {{last_name}} at {{company_name}}, return a JSON object with: title (current job title), linkedin_url (LinkedIn profile URL if found in the research), location (city, state), and seniority_level (C-Suite, VP, Director, Manager, Individual Contributor). Only use facts from the research — do not fabricate URLs.",
        ai_model: "sonnet",
      },
    ],
  },
  {
    id: "email-waterfall",
    name: "Email Waterfall",
    description:
      "Find verified emails using multiple providers — tries Findymail first, falls back to web search for maximum coverage.",
    category: "enrichment",
    icon: "Layers",
    expected_inputs: [
      { name: "first_name", description: "Contact's first name", required: true },
      { name: "last_name", description: "Contact's last name", required: true },
      { name: "domain", description: "Company website domain", required: true },
    ],
    produced_outputs: [
      { name: "email", description: "Verified work email" },
      { name: "source", description: "Which provider found it" },
    ],
    columns: [
      {
        name: "Email (Waterfall)",
        column_type: "waterfall",
        output_key: "email",
      },
    ],
  },
  {
    id: "find-linkedin",
    name: "Find LinkedIn Profiles",
    description:
      "Look up LinkedIn profile URLs for your contacts using web search — finds real profile links, not guesses.",
    category: "enrichment",
    icon: "Linkedin",
    expected_inputs: [
      { name: "first_name", description: "Contact's first name", required: true },
      { name: "last_name", description: "Contact's last name", required: true },
      { name: "company_name", description: "Company name", required: true },
    ],
    produced_outputs: [
      { name: "linkedin_url", description: "LinkedIn profile URL" },
    ],
    columns: [
      {
        name: "LinkedIn Lookup",
        column_type: "enrichment",
        tool: "apollo_people_match",
        params: {
          first_name: "{{first_name}}",
          last_name: "{{last_name}}",
          organization_name: "{{company_name}}",
        },
        output_key: "results",
      },
      {
        name: "LinkedIn URL",
        column_type: "ai",
        ai_prompt:
          'From the LinkedIn Lookup results, extract the LinkedIn profile URL for {{first_name}} {{last_name}} at {{company_name}}. Return a JSON object with: linkedin_url (the full linkedin.com/in/ URL if found, or null), confidence (high/medium/low based on how well the result matches the name and company).',
        ai_model: "sonnet",
      },
    ],
  },
  {
    id: "company-contact-combo",
    name: "Company + Contact Research",
    description:
      "Two-in-one: research the company via web search and enrich the contact via Findymail in a single run.",
    category: "research",
    icon: "Sparkles",
    expected_inputs: [
      { name: "first_name", description: "Contact's first name", required: true },
      { name: "last_name", description: "Contact's last name", required: true },
      { name: "domain", description: "Company website domain", required: true },
      { name: "company_name", description: "Company name", required: false },
    ],
    produced_outputs: [
      { name: "company_summary", description: "What the company does" },
      { name: "contact_title", description: "Contact's job title" },
      { name: "email", description: "Verified work email" },
    ],
    columns: [
      {
        name: "Company Research",
        column_type: "enrichment",
        tool: "apollo_organization_enrich",
        params: {
          domain: "{{domain}}",
        },
        output_key: "results",
      },
      {
        name: "Email",
        column_type: "enrichment",
        tool: "dropleads_email_finder",
        params: {
          first_name: "{{first_name}}",
          last_name: "{{last_name}}",
          company_domain: "{{domain}}",
        },
        output_key: "email",
      },
      {
        name: "Contact Lookup",
        column_type: "enrichment",
        tool: "apollo_people_match",
        params: {
          first_name: "{{first_name}}",
          last_name: "{{last_name}}",
          domain: "{{domain}}",
        },
        output_key: "results",
      },
      {
        name: "Summary",
        column_type: "ai",
        ai_prompt:
          "Using the Company Research and Contact Lookup data, return a JSON object with: company_name (official name), company_summary (2-3 sentences about what they do), employee_count (estimated), industry (primary), contact_title (job title of {{first_name}} {{last_name}}), seniority_level (C-Suite/VP/Director/Manager/IC), linkedin_url (if found in research). Only use facts from the research.",
        ai_model: "sonnet",
      },
    ],
  },
];
