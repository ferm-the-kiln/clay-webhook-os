"use client";

import { useState } from "react";
import { Header } from "@/components/layout/header";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Target, FileText, Users, MessageSquare } from "lucide-react";

export default function ScoringPage() {
  const [activeTab, setActiveTab] = useState("discovery");

  // Discovery Questions state
  const [meetingType, setMeetingType] = useState("");
  const [discoveryResult, setDiscoveryResult] = useState<string | null>(null);

  // Campaign Brief state
  const [campaignName, setCampaignName] = useState("");
  const [targetPersona, setTargetPersona] = useState("");
  const [valueProp, setValueProp] = useState("");
  const [briefResult, setBriefResult] = useState<string | null>(null);

  // Committee Map state
  const [companyName, setCompanyName] = useState("");
  const [committeeResult, setCommitteeResult] = useState<string | null>(null);

  return (
    <div className="min-h-screen">
      <Header
        title="Scoring"
        breadcrumbs={[
          { label: "Analyze", href: "/analyze" },
          { label: "Scoring" },
        ]}
      />

      <main className="px-4 md:px-6 py-6 pb-20 md:pb-6">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-transparent gap-1 mb-6">
            <TabsTrigger
              value="discovery"
              className="data-[state=active]:bg-kiln-indigo/10 data-[state=active]:text-kiln-indigo text-clay-400"
            >
              <MessageSquare className="h-4 w-4" />
              Discovery Questions
            </TabsTrigger>
            <TabsTrigger
              value="brief"
              className="data-[state=active]:bg-kiln-indigo/10 data-[state=active]:text-kiln-indigo text-clay-400"
            >
              <FileText className="h-4 w-4" />
              Campaign Brief
            </TabsTrigger>
            <TabsTrigger
              value="committee"
              className="data-[state=active]:bg-kiln-indigo/10 data-[state=active]:text-kiln-indigo text-clay-400"
            >
              <Users className="h-4 w-4" />
              Committee Map
            </TabsTrigger>
          </TabsList>

          {/* Discovery Questions Tab */}
          <TabsContent value="discovery">
            <Card className="border-clay-800 bg-white shadow-sm rounded-xl">
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="text-xs text-clay-500 uppercase tracking-wider mb-1.5 block">
                      Meeting Type
                    </label>
                    <select
                      value={meetingType}
                      onChange={(e) => setMeetingType(e.target.value)}
                      className="w-full rounded-lg border border-clay-800 bg-clay-900 text-clay-200 px-3 py-2 text-sm"
                    >
                      <option value="">Select meeting type...</option>
                      <option value="discovery">Discovery Call</option>
                      <option value="demo">Product Demo</option>
                      <option value="follow-up">Follow-Up</option>
                      <option value="negotiation">Negotiation</option>
                      <option value="qbr">Quarterly Business Review</option>
                    </select>
                  </div>

                  <Button
                    className="bg-kiln-indigo text-white hover:bg-kiln-indigo-light font-semibold"
                    disabled={!meetingType}
                  >
                    <Target className="h-4 w-4" />
                    Generate Questions
                  </Button>
                </div>

                {/* Results area */}
                {discoveryResult ? (
                  <div className="mt-6 rounded-lg border border-clay-800 bg-clay-900 p-4">
                    <pre className="text-sm text-clay-200 whitespace-pre-wrap">
                      {discoveryResult}
                    </pre>
                  </div>
                ) : (
                  <div className="mt-6 flex flex-col items-center justify-center rounded-lg border border-dashed border-clay-800 bg-clay-900/50 p-8 text-center">
                    <MessageSquare className="h-8 w-8 text-clay-600 mb-3" />
                    <p className="text-sm text-clay-500">
                      Select a meeting type and generate tailored discovery questions.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Campaign Brief Tab */}
          <TabsContent value="brief">
            <Card className="border-clay-800 bg-white shadow-sm rounded-xl">
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="text-xs text-clay-500 uppercase tracking-wider mb-1.5 block">
                      Campaign Name
                    </label>
                    <input
                      type="text"
                      value={campaignName}
                      onChange={(e) => setCampaignName(e.target.value)}
                      placeholder="e.g. Q2 Enterprise Outbound"
                      className="w-full rounded-lg border border-clay-800 bg-clay-900 text-clay-200 px-3 py-2 text-sm"
                    />
                  </div>

                  <div>
                    <label className="text-xs text-clay-500 uppercase tracking-wider mb-1.5 block">
                      Target Persona
                    </label>
                    <input
                      type="text"
                      value={targetPersona}
                      onChange={(e) => setTargetPersona(e.target.value)}
                      placeholder="e.g. VP of Engineering at Series B+ startups"
                      className="w-full rounded-lg border border-clay-800 bg-clay-900 text-clay-200 px-3 py-2 text-sm"
                    />
                  </div>

                  <div>
                    <label className="text-xs text-clay-500 uppercase tracking-wider mb-1.5 block">
                      Value Proposition
                    </label>
                    <input
                      type="text"
                      value={valueProp}
                      onChange={(e) => setValueProp(e.target.value)}
                      placeholder="e.g. Reduce deployment time by 80% with zero-config CI/CD"
                      className="w-full rounded-lg border border-clay-800 bg-clay-900 text-clay-200 px-3 py-2 text-sm"
                    />
                  </div>

                  <Button
                    className="bg-kiln-indigo text-white hover:bg-kiln-indigo-light font-semibold"
                    disabled={!campaignName || !targetPersona || !valueProp}
                  >
                    <FileText className="h-4 w-4" />
                    Generate Brief
                  </Button>
                </div>

                {/* Results area */}
                {briefResult ? (
                  <div className="mt-6 rounded-lg border border-clay-800 bg-clay-900 p-4">
                    <pre className="text-sm text-clay-200 whitespace-pre-wrap">
                      {briefResult}
                    </pre>
                  </div>
                ) : (
                  <div className="mt-6 flex flex-col items-center justify-center rounded-lg border border-dashed border-clay-800 bg-clay-900/50 p-8 text-center">
                    <FileText className="h-8 w-8 text-clay-600 mb-3" />
                    <p className="text-sm text-clay-500">
                      Fill in the campaign details to generate a strategic brief.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Committee Map Tab */}
          <TabsContent value="committee">
            <Card className="border-clay-800 bg-white shadow-sm rounded-xl">
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="text-xs text-clay-500 uppercase tracking-wider mb-1.5 block">
                      Company Name
                    </label>
                    <input
                      type="text"
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      placeholder="e.g. Acme Corp"
                      className="w-full rounded-lg border border-clay-800 bg-clay-900 text-clay-200 px-3 py-2 text-sm"
                    />
                  </div>

                  <Button
                    className="bg-kiln-indigo text-white hover:bg-kiln-indigo-light font-semibold"
                    disabled={!companyName}
                  >
                    <Users className="h-4 w-4" />
                    Map Committee
                  </Button>
                </div>

                {/* Results area */}
                {committeeResult ? (
                  <div className="mt-6 rounded-lg border border-clay-800 bg-clay-900 p-4">
                    <pre className="text-sm text-clay-200 whitespace-pre-wrap">
                      {committeeResult}
                    </pre>
                  </div>
                ) : (
                  <div className="mt-6 flex flex-col items-center justify-center rounded-lg border border-dashed border-clay-800 bg-clay-900/50 p-8 text-center">
                    <Users className="h-8 w-8 text-clay-600 mb-3" />
                    <p className="text-sm text-clay-500">
                      Enter a company name to map the buying committee.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
