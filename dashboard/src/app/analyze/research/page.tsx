"use client";

import { useState } from "react";
import { Header } from "@/components/layout/header";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Search, Building2, Users, Swords } from "lucide-react";

const inputClass =
  "w-full rounded-lg border border-clay-800 bg-clay-900 text-clay-200 px-3 py-2 text-sm placeholder:text-clay-600 focus:outline-none focus:ring-1 focus:ring-kiln-indigo/50 focus:border-kiln-indigo/50";

const triggerClass =
  "data-[state=active]:bg-kiln-indigo/10 data-[state=active]:text-kiln-indigo text-clay-400";

type ResearchTab = "account" | "meeting" | "competitive";

interface FormFields {
  company_name: string;
  first_name: string;
  title: string;
}

const emptyFields: FormFields = { company_name: "", first_name: "", title: "" };

export default function ResearchPage() {
  const [activeTab, setActiveTab] = useState<ResearchTab>("account");
  const [fields, setFields] = useState<Record<ResearchTab, FormFields>>({
    account: { ...emptyFields },
    meeting: { ...emptyFields },
    competitive: { ...emptyFields },
  });

  const update = (tab: ResearchTab, key: keyof FormFields, value: string) => {
    setFields((prev) => ({
      ...prev,
      [tab]: { ...prev[tab], [key]: value },
    }));
  };

  const tabConfig: { value: ResearchTab; label: string; icon: React.ReactNode; description: string }[] = [
    {
      value: "account",
      label: "Account Research",
      icon: <Building2 className="h-4 w-4" />,
      description: "Deep-dive into a target account — firmographics, recent news, tech stack, and strategic signals.",
    },
    {
      value: "meeting",
      label: "Meeting Prep",
      icon: <Users className="h-4 w-4" />,
      description: "Prepare a briefing for an upcoming meeting — attendee backgrounds, talking points, and risk flags.",
    },
    {
      value: "competitive",
      label: "Competitive Analysis",
      icon: <Swords className="h-4 w-4" />,
      description: "Analyze competitive positioning — strengths, weaknesses, and differentiation strategies.",
    },
  ];

  const renderForm = (tab: ResearchTab) => {
    const f = fields[tab];
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-clay-300">Company Name</label>
            <input
              type="text"
              placeholder="e.g. Acme Corp"
              className={inputClass}
              value={f.company_name}
              onChange={(e) => update(tab, "company_name", e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-clay-300">First Name</label>
            <input
              type="text"
              placeholder="e.g. Sarah"
              className={inputClass}
              value={f.first_name}
              onChange={(e) => update(tab, "first_name", e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-clay-300">Title</label>
            <input
              type="text"
              placeholder="e.g. VP of Engineering"
              className={inputClass}
              value={f.title}
              onChange={(e) => update(tab, "title", e.target.value)}
            />
          </div>
        </div>
        <div>
          <Button
            className="bg-kiln-indigo text-white hover:bg-kiln-indigo-light font-semibold"
            disabled={!f.company_name.trim()}
          >
            <Search className="h-4 w-4 mr-2" />
            Run Research
          </Button>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Research"
        breadcrumbs={[
          { label: "Analyze", href: "/analyze" },
          { label: "Research" },
        ]}
      />

      <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 pb-20 md:pb-6 space-y-6">
        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as ResearchTab)}
        >
          <TabsList className="bg-clay-900 border border-clay-800 rounded-lg">
            {tabConfig.map((t) => (
              <TabsTrigger key={t.value} value={t.value} className={triggerClass}>
                {t.icon}
                <span className="hidden sm:inline ml-1.5">{t.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>

          {tabConfig.map((t) => (
            <TabsContent key={t.value} value={t.value} className="mt-4">
              <Card className="border-clay-800 bg-white shadow-sm rounded-xl">
                <CardContent className="p-6 space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold text-clay-100 flex items-center gap-2">
                      {t.icon}
                      {t.label}
                    </h3>
                    <p className="text-sm text-clay-500 mt-1">{t.description}</p>
                  </div>
                  {renderForm(t.value)}
                </CardContent>
              </Card>
            </TabsContent>
          ))}
        </Tabs>

        {/* Results section */}
        <Card className="border-clay-800 bg-white shadow-sm rounded-xl">
          <CardContent className="p-6">
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="rounded-full bg-clay-900 p-3 mb-4">
                <Search className="h-6 w-6 text-clay-500" />
              </div>
              <h3 className="text-sm font-medium text-clay-300">No results yet</h3>
              <p className="text-sm text-clay-500 mt-1 max-w-sm">
                Run a research query to see results here
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
