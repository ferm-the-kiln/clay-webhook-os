"use client";

import { useState } from "react";
import { X, Sparkles, Search, Mail, Building2, Users, Globe } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { TableDefinition } from "@/lib/types";

interface Suggestion {
  id: string;
  label: string;
  toolId: string;
  icon: typeof Search;
  color: string;
}

interface ColumnSuggestionsBarProps {
  table: TableDefinition;
  onAddSuggestion: (toolId: string, name: string) => void;
}

function getSuggestions(table: TableDefinition): Suggestion[] {
  const colNames = new Set(
    table.columns.map((c) => c.name.toLowerCase()),
  );
  const colIds = new Set(table.columns.map((c) => c.id));
  const enrichmentCols = table.columns.filter(
    (c) => c.column_type !== "input" && c.column_type !== "static",
  );

  // Don't show if there are already enrichment columns
  if (enrichmentCols.length > 0) return [];

  // Don't show if there are no input columns
  const inputCols = table.columns.filter((c) => c.column_type === "input");
  if (inputCols.length === 0) return [];

  const suggestions: Suggestion[] = [];

  const hasDomain = colNames.has("domain") || colNames.has("website") || colIds.has("domain") || colIds.has("website");
  const hasCompany = colNames.has("company") || colNames.has("company_name") || colIds.has("company") || colIds.has("company_name");
  const hasName = colNames.has("name") || colNames.has("first_name") || colNames.has("full_name");
  const hasLinkedin = colNames.has("linkedin") || colNames.has("linkedin_url");

  if (hasDomain) {
    suggestions.push({
      id: "company-research",
      label: "Company Research",
      toolId: "web_search",
      icon: Globe,
      color: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    });
    suggestions.push({
      id: "email-finding",
      label: "Email Finding",
      toolId: "findymail",
      icon: Mail,
      color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    });
  }

  if (hasCompany && !hasDomain) {
    suggestions.push({
      id: "company-enrichment",
      label: "Company Enrichment",
      toolId: "apollo_org",
      icon: Building2,
      color: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    });
    suggestions.push({
      id: "web-search",
      label: "Web Search",
      toolId: "web_search",
      icon: Search,
      color: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    });
  }

  if (hasName || hasLinkedin) {
    suggestions.push({
      id: "people-research",
      label: "People Research",
      toolId: "apollo_people",
      icon: Users,
      color: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    });
  }

  // Always suggest web search if nothing else matches
  if (suggestions.length === 0) {
    suggestions.push({
      id: "web-search",
      label: "Web Search",
      toolId: "web_search",
      icon: Search,
      color: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    });
  }

  return suggestions;
}

export function ColumnSuggestionsBar({
  table,
  onAddSuggestion,
}: ColumnSuggestionsBarProps) {
  const [dismissed, setDismissed] = useState(false);
  const suggestions = getSuggestions(table);

  if (dismissed || suggestions.length === 0) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: "auto" }}
        exit={{ opacity: 0, height: 0 }}
        className="shrink-0 border-b border-zinc-800 bg-gradient-to-r from-zinc-900 to-zinc-950 px-4 py-2"
      >
        <div className="flex items-center gap-3">
          <Sparkles className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span className="text-xs text-zinc-400 shrink-0">
            Based on your data, try:
          </span>

          <div className="flex items-center gap-2 flex-1 overflow-x-auto">
            {suggestions.map((s) => {
              const Icon = s.icon;
              return (
                <button
                  key={s.id}
                  onClick={() => onAddSuggestion(s.toolId, s.label)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium hover:brightness-125 transition-all shrink-0 ${s.color}`}
                >
                  <Icon className="w-3 h-3" />
                  {s.label}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setDismissed(true)}
            className="p-1 rounded hover:bg-zinc-800 text-zinc-600 hover:text-zinc-400 shrink-0"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
