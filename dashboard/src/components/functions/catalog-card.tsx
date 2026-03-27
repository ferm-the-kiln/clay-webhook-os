"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Play, Table2, MessageSquareText, Loader2 } from "lucide-react";
import type { FunctionDefinition } from "@/lib/types";
import { explainFunction } from "@/lib/api";

interface CatalogCardProps {
  func: FunctionDefinition;
  isFavorite?: boolean;
  onToggleFavorite?: (id: string) => void;
}

export function CatalogCard({
  func,
  isFavorite,
  onToggleFavorite,
}: CatalogCardProps) {
  const router = useRouter();
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);

  const handleExplain = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (explanation) { setExplanation(null); return; }
    setExplaining(true);
    try {
      const result = await explainFunction(func.id);
      setExplanation(result.explanation);
    } catch {
      setExplanation("Could not generate explanation");
    } finally {
      setExplaining(false);
    }
  };

  return (
    <Card className="border-clay-600 hover:border-clay-500 group transition-all">
      <CardContent className="p-4 flex flex-col h-full">
        <div className="flex items-start justify-between mb-1.5">
          <h4 className="text-sm font-medium text-clay-100 line-clamp-1 flex-1">
            {func.name}
          </h4>
          {onToggleFavorite && (
            <button
              onClick={() => onToggleFavorite(func.id)}
              className="text-clay-300 hover:text-amber-400 transition-colors shrink-0 ml-2"
              title={isFavorite ? "Remove from favorites" : "Add to favorites"}
            >
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill={isFavorite ? "currentColor" : "none"}
                stroke="currentColor"
                strokeWidth={2}
              >
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
              </svg>
            </button>
          )}
        </div>

        {func.description && (
          <p className="text-xs text-clay-300 line-clamp-2 mb-3 flex-1">
            {func.description}
          </p>
        )}

        {/* Input/output count badges */}
        <div className="flex items-center gap-2 mb-2">
          <Badge
            variant="outline"
            className="text-[10px] border-clay-600 text-clay-300 py-0"
          >
            {func.inputs.length} input{func.inputs.length !== 1 && "s"}
          </Badge>
          <Badge
            variant="outline"
            className="text-[10px] border-clay-600 text-clay-300 py-0"
          >
            {func.outputs.length} output{func.outputs.length !== 1 && "s"}
          </Badge>
          <button
            onClick={handleExplain}
            disabled={explaining}
            className="ml-auto text-clay-400 hover:text-kiln-teal transition-colors"
            title="Explain this function"
          >
            {explaining ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <MessageSquareText className="h-3.5 w-3.5" />
            )}
          </button>
        </div>

        {/* AI Explanation */}
        {explanation && (
          <p className="text-[10px] text-clay-300 bg-clay-900/50 rounded px-2 py-1.5 mb-2 line-clamp-3">
            {explanation}
          </p>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => router.push(`/run/${func.id}`)}
            className="flex-1 h-8 bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light text-xs font-semibold"
          >
            <Play className="h-3.5 w-3.5 mr-1" />
            Run
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push(`/workbench?function=${func.id}`)}
            className="flex-1 h-8 border-clay-600 text-clay-200 hover:bg-clay-700 text-xs"
          >
            <Table2 className="h-3.5 w-3.5 mr-1" />
            Batch
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
