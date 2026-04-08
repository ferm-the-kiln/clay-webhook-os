"use client";

import { useParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useFunctionTable } from "@/hooks/use-function-table";
import { FunctionSpreadsheet } from "@/components/functions/function-spreadsheet";

export default function FunctionDetailPage() {
  const params = useParams();
  const funcId = params.id as string;
  const ft = useFunctionTable(funcId);

  if (ft.loading) {
    return (
      <div className="min-h-screen bg-clay-950 flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-clay-300 animate-spin" />
      </div>
    );
  }

  if (ft.error || !ft.table) {
    return (
      <div className="min-h-screen bg-clay-950 flex items-center justify-center">
        <p className="text-red-400">{ft.error || "Function not found"}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-clay-950 text-white flex flex-col">
      <FunctionSpreadsheet ft={ft} />
    </div>
  );
}
