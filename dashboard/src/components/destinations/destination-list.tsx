"use client";

import type { Destination } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Pencil, Trash2, Zap } from "lucide-react";

interface DestinationListProps {
  destinations: Destination[];
  onEdit: (dest: Destination) => void;
  onDelete: (dest: Destination) => void;
  onTest: (dest: Destination) => void;
  testingId?: string | null;
}

export function DestinationList({
  destinations,
  onEdit,
  onDelete,
  onTest,
  testingId,
}: DestinationListProps) {
  if (destinations.length === 0) {
    return (
      <div className="rounded-xl border border-clay-800 bg-clay-900 p-8 text-center">
        <p className="text-clay-500 text-sm">
          No destinations configured yet. Add one to start pushing results.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-clay-800 bg-clay-900 overflow-hidden">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-clay-800 hover:bg-transparent">
              <TableHead className="text-clay-500 text-xs">Name</TableHead>
              <TableHead className="text-clay-500 text-xs">Type</TableHead>
              <TableHead className="text-clay-500 text-xs">URL</TableHead>
              <TableHead className="text-clay-500 text-xs">Client</TableHead>
              <TableHead className="text-clay-500 text-xs text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {destinations.map((dest) => (
              <TableRow key={dest.id} className="border-clay-800 hover:bg-clay-800/50">
                <TableCell className="text-clay-200 text-sm font-medium">
                  {dest.name}
                </TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className={
                      dest.type === "clay_webhook"
                        ? "border-kiln-teal/30 text-kiln-teal bg-kiln-teal/10"
                        : "border-kiln-mustard/30 text-kiln-mustard bg-kiln-mustard/10"
                    }
                  >
                    {dest.type === "clay_webhook" ? "Clay" : "Webhook"}
                  </Badge>
                </TableCell>
                <TableCell className="text-clay-400 text-xs font-[family-name:var(--font-mono)] max-w-[200px] truncate">
                  {dest.url}
                </TableCell>
                <TableCell className="text-clay-500 text-xs">
                  {dest.client_slug || "\u2014"}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => onTest(dest)}
                      disabled={testingId === dest.id}
                      className="text-clay-500 hover:text-kiln-teal"
                      title="Test connectivity"
                    >
                      <Zap className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => onEdit(dest)}
                      className="text-clay-500 hover:text-clay-200"
                      title="Edit"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => onDelete(dest)}
                      className="text-clay-500 hover:text-kiln-coral"
                      title="Delete"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
