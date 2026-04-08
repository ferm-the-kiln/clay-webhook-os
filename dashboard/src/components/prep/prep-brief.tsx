"use client";

import { Button } from "@/components/ui/button";
import { PrepSection } from "./prep-section";
import {
  FileText,
  MessageSquare,
  HelpCircle,
  Swords,
  AlertTriangle,
  Compass,
  Copy,
  Printer,
  RotateCcw,
} from "lucide-react";
import { toast } from "sonner";
import type { PrepSkillKey, SkillResultState, PrepInputs } from "@/lib/prep-types";

interface PrepBriefProps {
  inputs: PrepInputs;
  skillStates: Record<PrepSkillKey, SkillResultState>;
  onRetry: (skill: PrepSkillKey) => void;
  onReset: () => void;
}

function getSkill(
  states: Record<PrepSkillKey, SkillResultState>,
  key: PrepSkillKey
): SkillResultState {
  return states[key] || { status: "pending", data: null, error: null, startedAt: null, completedAt: null };
}

function renderList(items: unknown): React.ReactNode {
  if (!Array.isArray(items)) return null;
  return (
    <ul className="space-y-1.5">
      {items.slice(0, 8).map((item, i) => {
        if (typeof item === "string") {
          return (
            <li key={i} className="text-xs text-clay-200 leading-relaxed pl-3 border-l-2 border-clay-600">
              {item}
            </li>
          );
        }
        if (typeof item === "object" && item !== null) {
          const obj = item as Record<string, unknown>;
          const main = obj.question || obj.point || obj.topic || obj.text || obj.name || "";
          const sub = obj.what_to_listen_for || obj.reasoning || obj.context || obj.why || "";
          return (
            <li key={i} className="pl-3 border-l-2 border-clay-600 space-y-0.5">
              <p className="text-xs font-medium text-clay-100">{String(main)}</p>
              {sub && <p className="text-[11px] text-clay-300">{String(sub)}</p>}
            </li>
          );
        }
        return null;
      })}
    </ul>
  );
}

export function PrepBrief({ inputs, skillStates, onRetry, onReset }: PrepBriefProps) {
  const meetingPrep = getSkill(skillStates, "meeting-prep");
  const discovery = getSkill(skillStates, "discovery-questions");
  const competitive = getSkill(skillStates, "competitive-response");
  const researcher = getSkill(skillStates, "account-researcher");
  const champion = getSkill(skillStates, "champion-enabler");

  const handleCopy = () => {
    const sections: string[] = [];
    sections.push(`# Call Brief: ${inputs.companyName}`);
    if (inputs.contactName) sections.push(`Contact: ${inputs.contactName} — ${inputs.contactTitle || "N/A"}`);
    sections.push("");

    if (meetingPrep.data) {
      sections.push("## Executive Summary");
      if (meetingPrep.data.one_liner) sections.push(String(meetingPrep.data.one_liner));
      if (meetingPrep.data.company_snapshot) sections.push(String(meetingPrep.data.company_snapshot));
      sections.push("");
    }

    if (meetingPrep.data?.talking_points) {
      sections.push("## Talking Points");
      const tp = meetingPrep.data.talking_points as unknown[];
      tp.forEach((p) => sections.push(`- ${typeof p === "string" ? p : JSON.stringify(p)}`));
      sections.push("");
    }

    if (discovery.data?.questions) {
      sections.push("## Discovery Questions");
      const q = discovery.data.questions as unknown[];
      q.forEach((item) => {
        if (typeof item === "string") sections.push(`- ${item}`);
        else if (typeof item === "object" && item) {
          const obj = item as Record<string, unknown>;
          sections.push(`- ${obj.question || obj.text || JSON.stringify(item)}`);
        }
      });
      sections.push("");
    }

    if (competitive.data) {
      sections.push("## Competitive Intel");
      if (competitive.data.response) sections.push(String(competitive.data.response));
      sections.push("");
    }

    navigator.clipboard.writeText(sections.join("\n"));
    toast.success("Brief copied to clipboard");
  };

  const handlePrint = () => window.print();

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between print:hidden">
        <h2 className="text-base font-semibold text-clay-100">
          {inputs.companyName}
          {inputs.contactName && (
            <span className="text-clay-300 font-normal">
              {" "}
              — {inputs.contactName}
            </span>
          )}
        </h2>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            className="h-7 text-xs border-clay-500 text-clay-200"
          >
            <Copy className="h-3 w-3 mr-1.5" /> Copy
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handlePrint}
            className="h-7 text-xs border-clay-500 text-clay-200"
          >
            <Printer className="h-3 w-3 mr-1.5" /> Print
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onReset}
            className="h-7 text-xs border-clay-500 text-clay-200"
          >
            <RotateCcw className="h-3 w-3 mr-1.5" /> New
          </Button>
        </div>
      </div>

      {/* Brief sections */}
      <div className="grid grid-cols-1 gap-4">
        {/* Executive Summary */}
        <PrepSection
          title="Executive Summary"
          icon={FileText}
          loading={meetingPrep.status === "running" || meetingPrep.status === "pending"}
          error={meetingPrep.error}
          onRetry={() => onRetry("meeting-prep")}
        >
          {meetingPrep.data && (
            <div className="space-y-2">
              {!!meetingPrep.data.one_liner && (
                <p className="text-sm font-medium text-clay-100">
                  {String(meetingPrep.data.one_liner)}
                </p>
              )}
              {!!meetingPrep.data.company_snapshot && (
                <p className="text-xs text-clay-200 leading-relaxed">
                  {String(meetingPrep.data.company_snapshot)}
                </p>
              )}
              {!!meetingPrep.data.person_context && (
                <p className="text-xs text-clay-200 leading-relaxed">
                  {String(meetingPrep.data.person_context)}
                </p>
              )}
            </div>
          )}
        </PrepSection>

        {/* Talking Points */}
        <PrepSection
          title="Talking Points"
          icon={MessageSquare}
          iconColor="text-blue-400"
          loading={
            (meetingPrep.status === "running" || meetingPrep.status === "pending") &&
            (champion.status === "running" || champion.status === "pending")
          }
          error={
            meetingPrep.status === "error" && champion.status === "error"
              ? "Both sources failed"
              : null
          }
          onRetry={() => {
            if (meetingPrep.status === "error") onRetry("meeting-prep");
            if (champion.status === "error") onRetry("champion-enabler");
          }}
        >
          <div className="space-y-3">
            {!!meetingPrep.data?.talking_points && renderList(meetingPrep.data.talking_points)}
            {!!champion.data?.key_talking_points && (
              <>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-clay-300 pt-2">
                  Champion enablement
                </p>
                {renderList(champion.data.key_talking_points)}
              </>
            )}
          </div>
        </PrepSection>

        {/* Discovery Questions */}
        <PrepSection
          title="Discovery Questions"
          icon={HelpCircle}
          iconColor="text-amber-400"
          loading={discovery.status === "running" || discovery.status === "pending"}
          error={discovery.error}
          onRetry={() => onRetry("discovery-questions")}
        >
          {discovery.data && (
            <div className="space-y-3">
              {!!discovery.data.opening_question && (
                <div className="pl-3 border-l-2 border-amber-400/30">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-400/70 mb-1">
                    Opening
                  </p>
                  <p className="text-xs font-medium text-clay-100">
                    {String(discovery.data.opening_question)}
                  </p>
                </div>
              )}
              {!!discovery.data.questions && renderList(discovery.data.questions)}
            </div>
          )}
        </PrepSection>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Competitive Intel */}
          <PrepSection
            title="Competitive Intel"
            icon={Swords}
            iconColor="text-red-400"
            loading={competitive.status === "running" || competitive.status === "pending"}
            error={competitive.error}
            onRetry={() => onRetry("competitive-response")}
          >
            {competitive.data && (
              <div className="space-y-2">
                {!!competitive.data.response && (
                  <p className="text-xs text-clay-200 leading-relaxed">
                    {String(competitive.data.response)}
                  </p>
                )}
                {!!competitive.data.trap_question && (
                  <div className="pl-3 border-l-2 border-red-400/30 mt-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-red-400/70 mb-0.5">
                      Trap question to set
                    </p>
                    <p className="text-xs text-clay-100">
                      {String(competitive.data.trap_question)}
                    </p>
                  </div>
                )}
                {!!competitive.data.when_we_win && (
                  <div className="pt-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-green-400/70 mb-0.5">
                      When we win
                    </p>
                    <p className="text-xs text-clay-200">
                      {String(competitive.data.when_we_win)}
                    </p>
                  </div>
                )}
              </div>
            )}
          </PrepSection>

          {/* Landmines & Risks */}
          <PrepSection
            title="Landmines & Risks"
            icon={AlertTriangle}
            iconColor="text-orange-400"
            loading={
              (meetingPrep.status === "running" || meetingPrep.status === "pending") &&
              (researcher.status === "running" || researcher.status === "pending")
            }
            error={
              meetingPrep.status === "error" && researcher.status === "error"
                ? "Both sources failed"
                : null
            }
          >
            <div className="space-y-2">
              {!!meetingPrep.data?.landmines && renderList(meetingPrep.data.landmines)}
              {Array.isArray(researcher.data?.negative_signals) &&
                (researcher.data.negative_signals as string[]).length > 0 && (
                  <>
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-clay-300 pt-1">
                      Negative signals
                    </p>
                    {renderList(researcher.data.negative_signals)}
                  </>
                )}
            </div>
          </PrepSection>
        </div>

        {/* Recommended Approach */}
        <PrepSection
          title="Recommended Approach"
          icon={Compass}
          iconColor="text-green-400"
          loading={
            (researcher.status === "running" || researcher.status === "pending") &&
            (champion.status === "running" || champion.status === "pending")
          }
          error={
            researcher.status === "error" && champion.status === "error"
              ? "Both sources failed"
              : null
          }
        >
          <div className="space-y-3">
            {!!researcher.data?.icp_fit_assessment && (
              <p className="text-xs text-clay-200 leading-relaxed">
                {String(researcher.data.icp_fit_assessment)}
              </p>
            )}
            {!!researcher.data?.recommended_angles &&
              renderList(researcher.data.recommended_angles)}
            {!!champion.data?.objection_preempts && (
              <>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-clay-300 pt-2">
                  Objection preempts
                </p>
                {renderList(champion.data.objection_preempts)}
              </>
            )}
            {!!champion.data?.next_step_suggestion && (
              <div className="pl-3 border-l-2 border-green-400/30 mt-2">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-green-400/70 mb-0.5">
                  Suggested next step
                </p>
                <p className="text-xs text-clay-100">
                  {String(champion.data.next_step_suggestion)}
                </p>
              </div>
            )}
          </div>
        </PrepSection>
      </div>
    </div>
  );
}
