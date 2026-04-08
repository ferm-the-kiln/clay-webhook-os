"use client";

import { CompanyOverviewCard } from "./company-overview-card";
import { KeyPeopleCard } from "./key-people-card";
import { IcpFitCard } from "./icp-fit-card";
import type { WebhookResponse } from "@/lib/types";
import type { SkillStatus, EntityType } from "@/hooks/use-research";

interface SkillState {
  status: SkillStatus;
  data: WebhookResponse | null;
  error: string | null;
}

interface DossierViewProps {
  entityType: EntityType;
  query: string;
  skillStates: Record<string, SkillState>;
  onRetry: (skill: string) => void;
}

export function DossierView({
  entityType,
  query,
  skillStates,
  onRetry,
}: DossierViewProps) {
  const get = (skill: string): SkillState =>
    skillStates[skill] || { status: "idle", data: null, error: null };

  const companyResearch = get("company-research");
  const peopleResearch = get("people-research");
  const accountResearcher = get("account-researcher");
  const companyQualifier = get("company-qualifier");

  return (
    <div className="mt-6 space-y-4">
      {/* Query header */}
      <div className="flex items-center gap-2">
        <h2 className="text-base font-semibold text-clay-100">{query}</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Company overview (or person summary) */}
        <CompanyOverviewCard
          data={companyResearch.data}
          status={companyResearch.status}
          error={companyResearch.error}
          onRetry={() => onRetry("company-research")}
        />

        {/* Key people */}
        <KeyPeopleCard
          data={peopleResearch.data}
          status={peopleResearch.status}
          error={peopleResearch.error}
          onRetry={() => onRetry("people-research")}
        />

        {/* ICP fit & angles — spans full width */}
        <IcpFitCard
          qualifierData={companyQualifier.data}
          qualifierStatus={
            entityType === "person" ? "idle" : companyQualifier.status
          }
          qualifierError={companyQualifier.error}
          researcherData={accountResearcher.data}
          researcherStatus={accountResearcher.status}
          researcherError={accountResearcher.error}
          onRetryQualifier={() => onRetry("company-qualifier")}
          onRetryResearcher={() => onRetry("account-researcher")}
        />
      </div>
    </div>
  );
}
