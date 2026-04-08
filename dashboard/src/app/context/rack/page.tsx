"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/header";
import {
  fetchRackConfig,
  fetchRackAnalytics,
  fetchRackItems,
  updateRackSlot,
  type RackSlot,
  type RackLoadEntry,
  type ContextItem,
} from "@/lib/api";
import { toast } from "sonner";
import {
  ArrowUp,
  ArrowDown,
  Database,
  FileText,
  Zap,
  BarChart3,
  Settings2,
  Layers,
  ToggleLeft,
  ToggleRight,
  RefreshCw,
  Package,
} from "lucide-react";

// ── Slot icon + color mapping ──

const SLOT_META: Record<
  string,
  { icon: typeof Layers; color: string; description: string }
> = {
  system: {
    icon: Zap,
    color: "text-yellow-500",
    description: "Format-aware system instructions",
  },
  skill: {
    icon: FileText,
    color: "text-blue-500",
    description: "Skill body from skill.md",
  },
  memory: {
    icon: Database,
    color: "text-purple-500",
    description: "Prior entity knowledge",
  },
  learnings: {
    icon: BarChart3,
    color: "text-orange-500",
    description: "Feedback corrections",
  },
  defaults: {
    icon: Package,
    color: "text-clay-300",
    description: "Auto-loaded defaults (writing style)",
  },
  knowledge: {
    icon: Layers,
    color: "text-green-500",
    description: "Skill-specific context files",
  },
  semantic: {
    icon: Database,
    color: "text-cyan-500",
    description: "Auto-discovered relevant context",
  },
  data: {
    icon: FileText,
    color: "text-indigo-500",
    description: "Input data payload (JSON)",
  },
  campaign: {
    icon: Settings2,
    color: "text-pink-500",
    description: "Campaign override instructions",
  },
  reminder: {
    icon: Zap,
    color: "text-amber-500",
    description: "Format-aware closing reminder",
  },
};

const PROVIDER_LABELS: Record<string, { label: string; badge: string }> = {
  file: { label: "File", badge: "bg-blue-500/10 text-blue-400" },
  supabase: { label: "Supabase", badge: "bg-green-500/10 text-green-400" },
  inline: { label: "Inline", badge: "bg-clay-300/10 text-clay-300" },
  hybrid: { label: "Hybrid", badge: "bg-purple-500/10 text-purple-400" },
};

export default function RackPage() {
  const [slots, setSlots] = useState<RackSlot[]>([]);
  const [items, setItems] = useState<ContextItem[]>([]);
  const [analytics, setAnalytics] = useState<RackLoadEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"slots" | "items" | "analytics">("slots");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [configRes, itemsRes, analyticsRes] = await Promise.all([
        fetchRackConfig(),
        fetchRackItems().catch(() => ({ items: [], source: "error" })),
        fetchRackAnalytics().catch(() => ({
          analytics: [],
          source: "error",
        })),
      ]);
      setSlots(configRes.slots);
      setItems(itemsRes.items);
      setAnalytics(analyticsRes.analytics);
    } catch (e) {
      toast.error("Failed to load rack config");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleToggle = async (slotName: string, enabled: boolean) => {
    try {
      await updateRackSlot({ slot_name: slotName, is_enabled: enabled });
      setSlots((prev) =>
        prev.map((s) =>
          s.slot_name === slotName ? { ...s, is_enabled: enabled } : s
        )
      );
      toast.success(`${slotName} ${enabled ? "enabled" : "disabled"}`);
    } catch {
      toast.error("Failed to update slot");
    }
  };

  const handleMove = async (slotName: string, direction: "up" | "down") => {
    const idx = slots.findIndex((s) => s.slot_name === slotName);
    if (idx < 0) return;
    const swapIdx = direction === "up" ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= slots.length) return;

    const currentOrder = slots[idx].slot_order;
    const swapOrder = slots[swapIdx].slot_order;

    try {
      await Promise.all([
        updateRackSlot({
          slot_name: slots[idx].slot_name,
          slot_order: swapOrder,
        }),
        updateRackSlot({
          slot_name: slots[swapIdx].slot_name,
          slot_order: currentOrder,
        }),
      ]);

      setSlots((prev) => {
        const updated = [...prev];
        updated[idx] = { ...updated[idx], slot_order: swapOrder };
        updated[swapIdx] = { ...updated[swapIdx], slot_order: currentOrder };
        return updated.sort((a, b) => a.slot_order - b.slot_order);
      });
      toast.success("Slot order updated");
    } catch {
      toast.error("Failed to reorder");
    }
  };

  // ── Analytics aggregation ──
  const tokensBySlot = analytics.reduce(
    (acc, entry) => {
      if (!entry.rack_slots) return acc;
      for (const rs of entry.rack_slots) {
        acc[rs.slot] = (acc[rs.slot] || 0) + rs.tokens;
      }
      return acc;
    },
    {} as Record<string, number>
  );

  const totalTokens = Object.values(tokensBySlot).reduce(
    (a, b) => a + b,
    0
  );

  const itemsByCategory = items.reduce(
    (acc, item) => {
      acc[item.category] = (acc[item.category] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="flex flex-col h-screen bg-[var(--bg-base)]">
      <Header title="Context Rack" />

      <div className="flex-1 overflow-auto p-6">
        {/* Tab bar */}
        <div className="flex gap-1 mb-6 bg-[var(--bg-elevated)] rounded-lg p-1 w-fit">
          {(
            [
              ["slots", "Pipeline", Layers],
              ["items", "Content", Database],
              ["analytics", "Analytics", BarChart3],
            ] as const
          ).map(([key, label, Icon]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                tab === key
                  ? "bg-[var(--bg-base)] text-[var(--text-primary)] shadow-sm"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}

          <button
            onClick={loadData}
            className="ml-2 p-2 rounded-md text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        {/* ── Pipeline Tab ── */}
        {tab === "slots" && (
          <div className="max-w-3xl space-y-3">
            <p className="text-sm text-[var(--text-secondary)] mb-4">
              Each slot is a stage in the prompt assembly pipeline. Slots run
              top-to-bottom, collecting context at each stage.
            </p>

            {slots.map((slot, idx) => {
              const meta = SLOT_META[slot.slot_name] || {
                icon: Layers,
                color: "text-clay-300",
                description: "",
              };
              const Icon = meta.icon;
              const providerInfo =
                PROVIDER_LABELS[slot.provider] || PROVIDER_LABELS.file;

              return (
                <div
                  key={slot.slot_name}
                  className={`flex items-center gap-4 p-4 rounded-xl border transition-all ${
                    slot.is_enabled
                      ? "bg-[var(--bg-elevated)] border-[var(--border-default)]"
                      : "bg-[var(--bg-base)] border-[var(--border-default)] opacity-50"
                  }`}
                >
                  {/* Order controls */}
                  <div className="flex flex-col gap-0.5">
                    <button
                      onClick={() => handleMove(slot.slot_name, "up")}
                      disabled={idx === 0}
                      className="p-1 rounded hover:bg-[var(--bg-base)] disabled:opacity-20"
                    >
                      <ArrowUp className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => handleMove(slot.slot_name, "down")}
                      disabled={idx === slots.length - 1}
                      className="p-1 rounded hover:bg-[var(--bg-base)] disabled:opacity-20"
                    >
                      <ArrowDown className="w-3 h-3" />
                    </button>
                  </div>

                  {/* Slot info */}
                  <div className={`${meta.color}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm text-[var(--text-primary)]">
                        {slot.slot_name}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${providerInfo.badge}`}
                      >
                        {providerInfo.label}
                      </span>
                      <span className="text-xs text-[var(--text-tertiary)]">
                        #{slot.slot_order}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                      {meta.description}
                    </p>
                  </div>

                  {/* Token contribution */}
                  {tokensBySlot[slot.slot_name] && (
                    <div className="text-right">
                      <div className="text-xs font-mono text-[var(--text-secondary)]">
                        {Math.round(
                          tokensBySlot[slot.slot_name]
                        ).toLocaleString()}{" "}
                        tok
                      </div>
                      <div className="w-20 h-1.5 bg-[var(--bg-base)] rounded-full mt-1 overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full"
                          style={{
                            width: `${totalTokens ? (tokensBySlot[slot.slot_name] / totalTokens) * 100 : 0}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Toggle */}
                  <button
                    onClick={() =>
                      handleToggle(slot.slot_name, !slot.is_enabled)
                    }
                    className="p-1"
                  >
                    {slot.is_enabled ? (
                      <ToggleRight className="w-6 h-6 text-green-500" />
                    ) : (
                      <ToggleLeft className="w-6 h-6 text-[var(--text-tertiary)]" />
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* ── Content Tab ── */}
        {tab === "items" && (
          <div className="max-w-4xl">
            <p className="text-sm text-[var(--text-secondary)] mb-4">
              {items.length} context items stored in Supabase across{" "}
              {Object.keys(itemsByCategory).length} categories.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mb-6">
              {Object.entries(itemsByCategory)
                .sort(([, a], [, b]) => b - a)
                .map(([cat, count]) => (
                  <div
                    key={cat}
                    className="bg-[var(--bg-elevated)] border border-[var(--border-default)] rounded-lg p-3"
                  >
                    <div className="text-2xl font-bold text-[var(--text-primary)]">
                      {count}
                    </div>
                    <div className="text-xs text-[var(--text-secondary)]">
                      {cat}
                    </div>
                  </div>
                ))}
            </div>

            <div className="border border-[var(--border-default)] rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[var(--bg-elevated)] text-[var(--text-secondary)] text-left">
                    <th className="px-4 py-3 font-medium">Title</th>
                    <th className="px-4 py-3 font-medium">Category</th>
                    <th className="px-4 py-3 font-medium">Type</th>
                    <th className="px-4 py-3 font-medium text-right">
                      Priority
                    </th>
                    <th className="px-4 py-3 font-medium text-right">Ver</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.id}
                      className="border-t border-[var(--border-default)] hover:bg-[var(--bg-elevated)]/50"
                    >
                      <td className="px-4 py-3 text-[var(--text-primary)] font-medium">
                        {item.title}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400">
                          {item.category}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[var(--text-secondary)]">
                        {item.item_type}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-[var(--text-secondary)]">
                        {item.priority_weight}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-[var(--text-secondary)]">
                        v{item.version}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Analytics Tab ── */}
        {tab === "analytics" && (
          <div className="max-w-4xl">
            {analytics.length === 0 ? (
              <div className="text-center py-16 text-[var(--text-secondary)]">
                <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-30" />
                <p className="text-lg font-medium">No analytics yet</p>
                <p className="text-sm mt-1">
                  Enable the rack with SUPABASE_CONTEXT_RACK_ENABLED=true
                  and run some skills to see data here.
                </p>
              </div>
            ) : (
              <>
                {/* Summary cards */}
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="bg-[var(--bg-elevated)] border border-[var(--border-default)] rounded-lg p-4">
                    <div className="text-2xl font-bold text-[var(--text-primary)]">
                      {analytics.length}
                    </div>
                    <div className="text-xs text-[var(--text-secondary)]">
                      Executions logged
                    </div>
                  </div>
                  <div className="bg-[var(--bg-elevated)] border border-[var(--border-default)] rounded-lg p-4">
                    <div className="text-2xl font-bold text-[var(--text-primary)]">
                      {Math.round(
                        analytics.reduce(
                          (sum, a) => sum + a.total_context_tokens,
                          0
                        ) / Math.max(analytics.length, 1)
                      ).toLocaleString()}
                    </div>
                    <div className="text-xs text-[var(--text-secondary)]">
                      Avg context tokens
                    </div>
                  </div>
                  <div className="bg-[var(--bg-elevated)] border border-[var(--border-default)] rounded-lg p-4">
                    <div className="text-2xl font-bold text-[var(--text-primary)]">
                      {Math.round(
                        analytics.reduce(
                          (sum, a) => sum + (a.assembly_ms || 0),
                          0
                        ) / Math.max(analytics.length, 1)
                      )}
                      ms
                    </div>
                    <div className="text-xs text-[var(--text-secondary)]">
                      Avg assembly time
                    </div>
                  </div>
                </div>

                {/* Recent executions table */}
                <div className="border border-[var(--border-default)] rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-[var(--bg-elevated)] text-[var(--text-secondary)] text-left">
                        <th className="px-4 py-3 font-medium">Skill</th>
                        <th className="px-4 py-3 font-medium">Client</th>
                        <th className="px-4 py-3 font-medium text-right">
                          Tokens
                        </th>
                        <th className="px-4 py-3 font-medium text-right">
                          Time
                        </th>
                        <th className="px-4 py-3 font-medium">Source</th>
                        <th className="px-4 py-3 font-medium">When</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analytics.slice(0, 25).map((entry, i) => (
                        <tr
                          key={i}
                          className="border-t border-[var(--border-default)]"
                        >
                          <td className="px-4 py-3 font-medium text-[var(--text-primary)]">
                            {entry.skill}
                          </td>
                          <td className="px-4 py-3 text-[var(--text-secondary)]">
                            {entry.client_slug || "-"}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-[var(--text-secondary)]">
                            {entry.total_context_tokens.toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-right font-mono text-[var(--text-secondary)]">
                            {entry.assembly_ms || "-"}ms
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`text-xs px-2 py-0.5 rounded-full ${
                                PROVIDER_LABELS[entry.source_mode]?.badge ||
                                "bg-clay-300/10 text-clay-300"
                              }`}
                            >
                              {entry.source_mode}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-xs text-[var(--text-tertiary)]">
                            {new Date(entry.created_at).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
