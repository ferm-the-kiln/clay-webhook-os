"use client";

import type { VariantDef } from "@/lib/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Edit2, Trash2, Copy } from "lucide-react";
import { formatRelativeTime } from "@/lib/utils";

export function VariantList({
  skill,
  variants,
  onEdit,
  onDelete,
  onFork,
}: {
  skill: string;
  variants: VariantDef[];
  onEdit: (v: VariantDef) => void;
  onDelete: (v: VariantDef) => void;
  onFork: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-medium text-clay-300">
            Variants for <span className="text-kiln-teal">{skill}</span>
          </h4>
          <p className="text-xs text-clay-500 mt-0.5">
            {variants.length} variant{variants.length !== 1 ? "s" : ""} + default
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onFork}
          className="border-clay-700 text-clay-300 hover:text-kiln-teal hover:border-kiln-teal/30"
        >
          <Copy className="h-3.5 w-3.5 mr-1.5" />
          Fork Current
        </Button>
      </div>

      {variants.length === 0 ? (
        <EmptyState
          title="No variants yet"
          description="Fork the current skill to create your first variant for A/B testing."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {/* Default card */}
          <Card className="border-clay-800 bg-clay-900 border-kiln-teal/20">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h5 className="font-medium text-clay-100 text-sm">Default</h5>
                  <Badge
                    variant="outline"
                    className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30 text-[10px]"
                  >
                    active
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-xs text-clay-500">
                Current production skill.md
              </p>
            </CardContent>
          </Card>

          {variants.map((v) => (
            <Card key={v.id} className="border-clay-800 bg-clay-900">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <h5 className="font-medium text-clay-100 text-sm truncate">
                    {v.label}
                  </h5>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 text-clay-500 hover:text-clay-200"
                      onClick={() => onEdit(v)}
                    >
                      <Edit2 className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 text-clay-500 hover:text-kiln-coral"
                      onClick={() => onDelete(v)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <p className="text-xs text-clay-500 font-[family-name:var(--font-mono)]">
                  {v.id}
                </p>
                <p className="text-xs text-clay-600 mt-1">
                  {formatRelativeTime(v.created_at)}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
