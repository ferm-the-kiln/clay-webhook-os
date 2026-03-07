"use client";

import { useState, useEffect } from "react";
import type { ClientProfile } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Loader2 } from "lucide-react";

interface ClientEditorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  client: ClientProfile | null; // null = create mode
  saving: boolean;
  onSave: (data: {
    slug: string;
    name: string;
    company: {
      domain: string;
      industry: string;
      size: string;
      stage: string;
      hq: string;
      founded: string;
    };
    what_they_sell: string;
    icp: string;
    competitive_landscape: string;
    recent_news: string;
    value_proposition: string;
    tone: { formality: string; approach: string; avoid: string };
    campaign_angles: string;
    notes: string;
    personas: string;
    battle_cards: string;
    signal_playbook: string;
    proven_responses: string;
    active_campaigns: string;
  }) => void;
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label className="text-xs font-medium text-clay-400 mb-1 block">
      {children}
    </label>
  );
}

function Field({
  label,
  value,
  onChange,
  disabled,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  placeholder?: string;
}) {
  return (
    <div>
      <Label>{label}</Label>
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder={placeholder}
        className="bg-clay-900 border-clay-700 text-clay-100 placeholder:text-clay-600"
      />
    </div>
  );
}

function TextArea({
  label,
  value,
  onChange,
  rows,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  rows?: number;
}) {
  return (
    <div>
      <Label>{label}</Label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows || 4}
        className="w-full rounded-md bg-clay-900 border border-clay-700 text-clay-100 placeholder:text-clay-600 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-kiln-teal/50 resize-y"
      />
    </div>
  );
}

export function ClientEditor({
  open,
  onOpenChange,
  client,
  saving,
  onSave,
}: ClientEditorProps) {
  const isEdit = client !== null;
  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [industry, setIndustry] = useState("");
  const [size, setSize] = useState("");
  const [stage, setStage] = useState("");
  const [hq, setHq] = useState("");
  const [founded, setFounded] = useState("");
  const [whatTheySell, setWhatTheySell] = useState("");
  const [icp, setIcp] = useState("");
  const [competitive, setCompetitive] = useState("");
  const [recentNews, setRecentNews] = useState("");
  const [valueProp, setValueProp] = useState("");
  const [formality, setFormality] = useState("");
  const [approach, setApproach] = useState("");
  const [avoid, setAvoid] = useState("");
  const [campaignAngles, setCampaignAngles] = useState("");
  const [notes, setNotes] = useState("");
  const [personas, setPersonas] = useState("");
  const [battleCards, setBattleCards] = useState("");
  const [signalPlaybook, setSignalPlaybook] = useState("");
  const [provenResponses, setProvenResponses] = useState("");
  const [activeCampaigns, setActiveCampaigns] = useState("");

  useEffect(() => {
    if (client) {
      setSlug(client.slug);
      setName(client.name);
      setDomain(client.company.domain);
      setIndustry(client.company.industry);
      setSize(client.company.size);
      setStage(client.company.stage);
      setHq(client.company.hq);
      setFounded(client.company.founded);
      setWhatTheySell(client.what_they_sell);
      setIcp(client.icp);
      setCompetitive(client.competitive_landscape);
      setRecentNews(client.recent_news);
      setValueProp(client.value_proposition);
      setFormality(client.tone.formality);
      setApproach(client.tone.approach);
      setAvoid(client.tone.avoid);
      setCampaignAngles(client.campaign_angles);
      setNotes(client.notes);
      setPersonas(client.personas || "");
      setBattleCards(client.battle_cards || "");
      setSignalPlaybook(client.signal_playbook || "");
      setProvenResponses(client.proven_responses || "");
      setActiveCampaigns(client.active_campaigns || "");
    } else {
      setSlug("");
      setName("");
      setDomain("");
      setIndustry("");
      setSize("");
      setStage("");
      setHq("");
      setFounded("");
      setWhatTheySell("");
      setIcp("");
      setCompetitive("");
      setRecentNews("");
      setValueProp("");
      setFormality("");
      setApproach("");
      setAvoid("");
      setCampaignAngles("");
      setNotes("");
      setPersonas("");
      setBattleCards("");
      setSignalPlaybook("");
      setProvenResponses("");
      setActiveCampaigns("");
    }
  }, [client, open]);

  const autoSlug = (n: string) =>
    n
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      slug: slug || autoSlug(name),
      name,
      company: { domain, industry, size, stage, hq, founded },
      what_they_sell: whatTheySell,
      icp,
      competitive_landscape: competitive,
      recent_news: recentNews,
      value_proposition: valueProp,
      tone: { formality, approach, avoid },
      campaign_angles: campaignAngles,
      notes,
      personas,
      battle_cards: battleCards,
      signal_playbook: signalPlaybook,
      proven_responses: provenResponses,
      active_campaigns: activeCampaigns,
    });
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl bg-clay-950 border-clay-800 overflow-y-auto"
      >
        <SheetHeader className="px-6 pt-6 pb-2">
          <SheetTitle className="text-clay-100">
            {isEdit ? `Edit ${client.name}` : "New Client Profile"}
          </SheetTitle>
          <SheetDescription className="text-clay-500">
            {isEdit
              ? "Update the client context used in prompt generation."
              : "Create a new client profile for prompt personalization."}
          </SheetDescription>
        </SheetHeader>
        <form onSubmit={handleSubmit} className="px-6 pb-6 space-y-6">
          {/* Identity */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-clay-300 border-b border-clay-800 pb-1">
              Identity
            </h4>
            <Field
              label="Client Name"
              value={name}
              onChange={(v) => {
                setName(v);
                if (!isEdit) setSlug(autoSlug(v));
              }}
              placeholder="e.g. Twelve Labs"
            />
            <Field
              label="Slug"
              value={slug}
              onChange={setSlug}
              disabled={isEdit}
              placeholder="auto-generated-from-name"
            />
          </div>

          {/* Company Info */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-clay-300 border-b border-clay-800 pb-1">
              Company Info
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Domain" value={domain} onChange={setDomain} placeholder="example.com" />
              <Field label="Industry" value={industry} onChange={setIndustry} placeholder="SaaS / AI" />
              <Field label="Size" value={size} onChange={setSize} placeholder="50-100 employees" />
              <Field label="Stage" value={stage} onChange={setStage} placeholder="Series B" />
              <Field label="HQ" value={hq} onChange={setHq} placeholder="San Francisco, CA" />
              <Field label="Founded" value={founded} onChange={setFounded} placeholder="2021" />
            </div>
          </div>

          {/* Content sections */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-clay-300 border-b border-clay-800 pb-1">
              Client Context
            </h4>
            <TextArea label="What They Sell" value={whatTheySell} onChange={setWhatTheySell} />
            <TextArea label="Target ICP" value={icp} onChange={setIcp} rows={6} />
            <TextArea label="Competitive Landscape" value={competitive} onChange={setCompetitive} />
            <TextArea label="Recent News" value={recentNews} onChange={setRecentNews} />
            <TextArea label="Value Proposition" value={valueProp} onChange={setValueProp} />
          </div>

          {/* Tone */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-clay-300 border-b border-clay-800 pb-1">
              Tone Preferences
            </h4>
            <Field label="Formality" value={formality} onChange={setFormality} placeholder="Technical but approachable" />
            <Field label="Approach" value={approach} onChange={setApproach} placeholder="Lead with capability" />
            <Field label="Things to Avoid" value={avoid} onChange={setAvoid} placeholder="Overpromising, vague claims" />
          </div>

          {/* Campaign */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-clay-300 border-b border-clay-800 pb-1">
              Campaign
            </h4>
            <TextArea label="Campaign Angles" value={campaignAngles} onChange={setCampaignAngles} rows={6} />
            <TextArea label="Notes" value={notes} onChange={setNotes} />
          </div>

          {/* GTM Context */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-clay-300 border-b border-clay-800 pb-1">
              GTM Context
            </h4>
            <TextArea label="Personas" value={personas} onChange={setPersonas} rows={6} />
            <TextArea label="Battle Cards" value={battleCards} onChange={setBattleCards} rows={6} />
            <TextArea label="Signal Playbook" value={signalPlaybook} onChange={setSignalPlaybook} rows={6} />
            <TextArea label="Proven Responses" value={provenResponses} onChange={setProvenResponses} rows={4} />
            <TextArea label="Active Campaigns" value={activeCampaigns} onChange={setActiveCampaigns} rows={4} />
          </div>

          <Button
            type="submit"
            disabled={saving || !name.trim()}
            className="w-full bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
          >
            {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            {isEdit ? "Save Changes" : "Create Client"}
          </Button>
        </form>
      </SheetContent>
    </Sheet>
  );
}
