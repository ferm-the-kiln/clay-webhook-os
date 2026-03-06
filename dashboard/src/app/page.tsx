import { Header } from "@/components/layout/header";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { JobList } from "@/components/dashboard/job-list";

export default function DashboardPage() {
  return (
    <div className="flex flex-col h-full">
      <Header title="Dashboard" />
      <div className="flex-1 overflow-auto p-6 space-y-6">
        <StatsCards />
        <div>
          <h3 className="text-sm text-zinc-500 uppercase tracking-wide mb-3">
            Recent Jobs
          </h3>
          <JobList />
        </div>
      </div>
    </div>
  );
}
