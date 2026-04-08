"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { QuickActionCard } from "@/components/home/quick-action-card";
import { RecentRunsSection } from "@/components/functions/recent-runs-section";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Upload,
  Sparkles,
  Play,
  Table2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  BarChart3,
} from "lucide-react";
import { getPersona, onPreferencesChanged } from "@/lib/user-preferences";
import { fetchTables, createTable, addTableColumn } from "@/lib/api";
import type { TableSummary, WorkflowTemplate } from "@/lib/types";
import { formatRelativeTime } from "@/lib/utils";
import { TemplateGallery } from "@/components/templates/template-gallery";
import { GettingStartedChecklist } from "@/components/onboarding/getting-started-checklist";
import { toast } from "sonner";

export function MyWorkDashboard() {
  const router = useRouter();
  const [tables, setTables] = useState<TableSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [showRecents, setShowRecents] = useState(false);
  const [persona, setPersona] = useState(getPersona);

  useEffect(() => {
    fetchTables()
      .then((r) => setTables(r.tables))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    return onPreferencesChanged(() => setPersona(getPersona()));
  }, []);

  const handleSelectTemplate = async (template: WorkflowTemplate) => {
    try {
      const table = await createTable({ name: template.name });
      for (const col of template.columns) {
        await addTableColumn(table.id, {
          name: col.name,
          column_type: col.column_type,
          tool: col.tool,
          params: col.params,
          ai_prompt: col.ai_prompt,
          ai_model: col.ai_model,
        });
      }
      toast.success(`Created "${template.name}" — upload a CSV to get started`);
      router.push(`/tables/${table.id}`);
    } catch {
      toast.error("Failed to create table from template");
    }
  };

  const recentTables = tables
    .sort((a, b) => b.updated_at - a.updated_at)
    .slice(0, 5);

  return (
    <div className="flex flex-col h-full">
      <Header title="Home" />
      <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
        {/* Welcome section */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-clay-100 mb-1">
            What would you like to do?
          </h2>
          <p className="text-sm text-clay-300">
            Upload a list, enrich your data, or run a quick lookup.
          </p>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8">
          <QuickActionCard
            icon={Upload}
            title="Upload & Enrich"
            subtitle="Import a CSV and add enrichments like email finding, company research, and more."
            accentColor="kiln-teal"
            onClick={() => router.push(persona === "rep" ? "/enrich" : "/tables?action=import")}
          />
          {persona === "rep" ? (
            <QuickActionCard
              icon={BarChart3}
              title="Recent Results"
              subtitle="View your latest enrichment runs and download results."
              accentColor="purple"
              onClick={() => {
                const latest = recentTables[0];
                if (latest) router.push(`/tables/${latest.id}`);
                else document.getElementById("recent-tables")?.scrollIntoView({ behavior: "smooth" });
              }}
            />
          ) : (
            <QuickActionCard
              icon={Sparkles}
              title="Build with AI"
              subtitle="Describe what you need in plain English and let AI set up the columns for you."
              accentColor="purple"
              onClick={() => router.push("/tables?action=ai-builder")}
            />
          )}
          <QuickActionCard
            icon={Play}
            title="Quick Run"
            subtitle="Run a single lookup using one of your saved functions."
            accentColor="amber"
            onClick={() => router.push("/chat")}
          />
        </div>

        {/* Getting Started Checklist */}
        <GettingStartedChecklist />

        {/* Template Gallery */}
        <div className="mb-8">
          <TemplateGallery
            onSelect={handleSelectTemplate}
            compact
            limit={4}
          />
        </div>

        {/* Recent Tables */}
        <div id="recent-tables" className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Table2 className="h-3.5 w-3.5 text-clay-300" />
            <h3 className="text-xs font-semibold text-clay-200 uppercase tracking-wider">
              Recent Tables
            </h3>
          </div>

          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="h-16 rounded-lg bg-clay-700/30 animate-pulse"
                />
              ))}
            </div>
          ) : recentTables.length === 0 ? (
            <Card className="border-clay-600 border-dashed">
              <CardContent className="p-6 text-center">
                <Table2 className="h-8 w-8 text-clay-400 mx-auto mb-2" />
                <p className="text-sm text-clay-300 mb-1">No tables yet</p>
                <p className="text-xs text-clay-400">
                  Upload a CSV or create a table to get started.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-1.5">
              {recentTables.map((table) => (
                <div
                  key={table.id}
                  onClick={() => router.push(`/tables/${table.id}`)}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-clay-700/30 transition-colors cursor-pointer group"
                >
                  <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-clay-700 shrink-0">
                    <Table2 className="h-4 w-4 text-clay-300" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-clay-100 truncate">
                        {table.name}
                      </span>
                      <Badge
                        variant="outline"
                        className="text-[10px] border-clay-500 text-clay-300 shrink-0"
                      >
                        {table.row_count} rows
                      </Badge>
                      {table.column_count > 0 && (
                        <Badge
                          variant="outline"
                          className="text-[10px] border-clay-500 text-clay-300 shrink-0"
                        >
                          {table.column_count} cols
                        </Badge>
                      )}
                    </div>
                    <p className="text-[11px] text-clay-400 mt-0.5">
                      Updated {formatRelativeTime(table.updated_at)}
                    </p>
                  </div>
                  <ExternalLink className="h-3.5 w-3.5 text-clay-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Runs — collapsible */}
        <div>
          <button
            onClick={() => setShowRecents(!showRecents)}
            className="flex items-center gap-2 mb-2 text-clay-300 hover:text-clay-200 transition-colors"
          >
            {showRecents ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
            <span className="text-xs font-semibold uppercase tracking-wider">
              Recent Quick Runs
            </span>
          </button>
          {showRecents && <RecentRunsSection />}
        </div>
      </div>
    </div>
  );
}
