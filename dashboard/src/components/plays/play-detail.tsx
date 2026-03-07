"use client";

import type { PlayDefinition } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ArrowLeft, GitFork, Settings2, ArrowRight } from "lucide-react";
import { CATEGORY_COLORS } from "./play-card";
import { cn } from "@/lib/utils";

interface PlayDetailProps {
  play: PlayDefinition;
  onBack: () => void;
  onClayConfig: () => void;
  onFork: () => void;
}

export function PlayDetail({ play, onBack, onClayConfig, onFork }: PlayDetailProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBack}
            className="text-clay-500 hover:text-clay-200 -ml-2 mb-1"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Plays
          </Button>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-clay-100">
              {play.display_name}
            </h2>
            <Badge
              variant="outline"
              className={cn("text-xs", CATEGORY_COLORS[play.category])}
            >
              {play.category}
            </Badge>
          </div>
          <p className="text-clay-400 max-w-2xl">{play.description}</p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            onClick={onFork}
            className="border-clay-700 text-clay-300 hover:text-clay-100"
          >
            <GitFork className="h-4 w-4 mr-1.5" />
            Fork
          </Button>
          <Button
            onClick={onClayConfig}
            className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
          >
            <Settings2 className="h-4 w-4 mr-1.5" />
            Setup in Clay
          </Button>
        </div>
      </div>

      {/* Info cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="border-clay-800 bg-clay-950">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-clay-400">When to Use</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-clay-200">{play.when_to_use}</p>
          </CardContent>
        </Card>
        <Card className="border-clay-800 bg-clay-950">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-clay-400">Who It&apos;s For</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-clay-200">{play.who_its_for}</p>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline visualization */}
      <Card className="border-clay-800 bg-clay-950">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-clay-400">Pipeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="outline" className="bg-clay-900 text-clay-200 border-clay-700 font-mono">
              {play.pipeline}
            </Badge>
            <span className="text-xs text-clay-600">|</span>
            <span className="text-xs text-clay-500">
              Model: {play.default_model} &middot; Confidence threshold: {play.default_confidence_threshold}
            </span>
          </div>
          {play.tags.length > 0 && (
            <div className="flex items-center gap-1.5 mt-3">
              {play.tags.map((tag) => (
                <Badge
                  key={tag}
                  variant="outline"
                  className="text-xs bg-clay-900 text-clay-500 border-clay-800"
                >
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Input schema */}
      <Card className="border-clay-800 bg-clay-950">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-clay-400">
            Input Schema
            <span className="ml-2 text-clay-600 font-normal">
              ({play.input_schema.length} fields)
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-clay-800 hover:bg-transparent">
                <TableHead className="text-clay-500">Field</TableHead>
                <TableHead className="text-clay-500">Type</TableHead>
                <TableHead className="text-clay-500">Required</TableHead>
                <TableHead className="text-clay-500">Description</TableHead>
                <TableHead className="text-clay-500">Example</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {play.input_schema.map((field) => (
                <TableRow key={field.name} className="border-clay-800">
                  <TableCell className="font-mono text-sm text-clay-200">
                    {field.name}
                  </TableCell>
                  <TableCell className="text-sm text-clay-400">
                    {field.type}
                  </TableCell>
                  <TableCell>
                    {field.required ? (
                      <Badge className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30 text-xs">
                        required
                      </Badge>
                    ) : (
                      <span className="text-xs text-clay-600">optional</span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-clay-400">
                    {field.description}
                  </TableCell>
                  <TableCell className="text-sm text-clay-500 font-mono">
                    {field.example || "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Output schema */}
      <Card className="border-clay-800 bg-clay-950">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-clay-400">
            Output Schema
            <span className="ml-2 text-clay-600 font-normal">
              ({play.output_schema.length} fields)
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-clay-800 hover:bg-transparent">
                <TableHead className="text-clay-500">Field</TableHead>
                <TableHead className="text-clay-500">Type</TableHead>
                <TableHead className="text-clay-500">Description</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {play.output_schema.map((field) => (
                <TableRow key={field.name} className="border-clay-800">
                  <TableCell className="font-mono text-sm text-clay-200">
                    {field.name}
                  </TableCell>
                  <TableCell className="text-sm text-clay-400">
                    {field.type}
                  </TableCell>
                  <TableCell className="text-sm text-clay-400">
                    {field.description}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
