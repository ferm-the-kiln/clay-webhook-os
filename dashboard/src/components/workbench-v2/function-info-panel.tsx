"use client";

import type { FunctionDefinition } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";

interface FunctionInfoPanelProps {
  func: FunctionDefinition;
}

export function FunctionInfoPanel({ func }: FunctionInfoPanelProps) {
  return (
    <Card className="bg-clay-900/50 border-clay-700">
      <CardContent className="p-4 space-y-4">
        {/* Inputs */}
        <div className="border-t border-clay-700/50 pt-4">
          <h4 className="text-xs font-medium text-clay-300 uppercase tracking-wider mb-2">
            Inputs ({func.inputs.length})
          </h4>
          <Table className="text-xs">
            <TableHeader>
              <TableRow>
                <TableHead>Field</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Required</TableHead>
                <TableHead>Description</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {func.inputs.map((input) => (
                <TableRow key={input.name}>
                  <TableCell className="font-mono">
                    {input.name}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="text-[10px]">
                      {input.type}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {input.required ? (
                      <Badge className="text-[10px] bg-kiln-teal/15 text-kiln-teal border-kiln-teal/25">
                        required
                      </Badge>
                    ) : (
                      <span className="text-clay-300">optional</span>
                    )}
                  </TableCell>
                  <TableCell className="text-clay-300">
                    {input.description || "\u2014"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Outputs */}
        <div className="border-t border-clay-700/50 pt-4">
          <h4 className="text-xs font-medium text-clay-300 uppercase tracking-wider mb-2">
            Outputs ({func.outputs.length})
          </h4>
          <Table className="text-xs">
            <TableHeader>
              <TableRow>
                <TableHead>Key</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Description</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {func.outputs.map((output) => (
                <TableRow key={output.key}>
                  <TableCell className="font-mono text-kiln-teal">
                    {output.key}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="text-[10px]">
                      {output.type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-clay-300">
                    {output.description || "\u2014"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Pipeline */}
        {func.steps.length > 0 && (
          <div className="border-t border-clay-700/50 pt-4">
            <h4 className="text-xs font-medium text-clay-300 uppercase tracking-wider mb-2">
              Pipeline ({func.steps.length})
            </h4>
            <div className="space-y-0">
              {func.steps.map((step, i) => (
                <div key={i} className="flex gap-3">
                  {/* Timeline */}
                  <div className="flex flex-col items-center">
                    <div className="flex items-center justify-center h-6 w-6 rounded-full bg-clay-800 border border-clay-600 text-[10px] font-bold text-kiln-teal shrink-0">
                      {i + 1}
                    </div>
                    {i < func.steps.length - 1 && (
                      <div className="w-px flex-1 bg-clay-700 min-h-[16px]" />
                    )}
                  </div>
                  {/* Content */}
                  <div className="pb-3 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-clay-100">
                        {formatToolName(step.tool)}
                      </span>
                    </div>
                    {Object.keys(step.params).length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {Object.entries(step.params).map(([k, v]) => (
                          <span
                            key={k}
                            className="text-[10px] text-clay-300 bg-clay-800 rounded px-1.5 py-0.5"
                          >
                            {k}={v}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function formatToolName(tool: string): string {
  if (tool.startsWith("skill:")) return tool;
  return tool
    .split(/[-_]/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
