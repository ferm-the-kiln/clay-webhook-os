import type { JobStatus } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

const STYLES: Record<JobStatus, string> = {
  queued: "bg-clay-700 text-clay-300 border-clay-600",
  processing: "bg-kiln-mustard/15 text-kiln-mustard border-kiln-mustard/30",
  completed: "bg-kiln-teal/15 text-kiln-teal border-kiln-teal/30",
  failed: "bg-kiln-coral/15 text-kiln-coral border-kiln-coral/30",
};

export function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <Badge variant="outline" className={STYLES[status]}>
      {status}
    </Badge>
  );
}
