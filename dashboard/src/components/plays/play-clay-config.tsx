"use client";

import { useState } from "react";
import type { PlayDefinition, ClayConfig, ClientSummary } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { generateClayConfig } from "@/lib/api";
import { Check, Clipboard, Loader2, Settings2 } from "lucide-react";
import { toast } from "sonner";

interface PlayClayConfigProps {
  play: PlayDefinition;
  clients: ClientSummary[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PlayClayConfig({
  play,
  clients,
  open,
  onOpenChange,
}: PlayClayConfigProps) {
  const [clientSlug, setClientSlug] = useState<string>("none");
  const [config, setConfig] = useState<ClayConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const result = await generateClayConfig(play.name, {
        client_slug: clientSlug !== "none" ? clientSlug : undefined,
      });
      setConfig(result);
    } catch (e) {
      toast.error("Failed to generate config", {
        description: (e as Error).message,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCopyBody = async () => {
    if (!config) return;
    const bodyJson = JSON.stringify(config.body_template, null, 2);
    await navigator.clipboard.writeText(bodyJson);
    setCopied(true);
    toast.success("Body template copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyFull = async () => {
    if (!config) return;
    await navigator.clipboard.writeText(JSON.stringify(config, null, 2));
    toast.success("Full config copied to clipboard");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-clay-800 bg-clay-950 max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-clay-100 flex items-center gap-2">
            <Settings2 className="h-5 w-5 text-kiln-teal" />
            Clay HTTP Action Config
          </DialogTitle>
          <DialogDescription className="text-clay-500">
            Generate the exact configuration to paste into Clay for &quot;{play.display_name}&quot;
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Client selector + Generate */}
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="text-xs text-clay-500 mb-1 block">
                Client (optional)
              </label>
              <Select value={clientSlug} onValueChange={setClientSlug}>
                <SelectTrigger className="border-clay-700 bg-clay-900 text-clay-200">
                  <SelectValue placeholder="No client" />
                </SelectTrigger>
                <SelectContent className="border-clay-700 bg-clay-900">
                  <SelectItem value="none">No client</SelectItem>
                  {clients.map((c) => (
                    <SelectItem key={c.slug} value={c.slug}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              onClick={handleGenerate}
              disabled={loading}
              className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
              ) : (
                <Settings2 className="h-4 w-4 mr-1.5" />
              )}
              Generate
            </Button>
          </div>

          {config && (
            <>
              {/* Setup instructions */}
              <Card className="border-clay-800 bg-clay-900">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-clay-400">
                    Setup Instructions
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ol className="space-y-1.5">
                    {config.setup_instructions.map((step, i) => (
                      <li key={i} className="text-sm text-clay-300">
                        {step}
                      </li>
                    ))}
                  </ol>
                </CardContent>
              </Card>

              {/* Body template (the money shot) */}
              <Card className="border-clay-800 bg-clay-900">
                <CardHeader className="pb-2 flex flex-row items-center justify-between">
                  <CardTitle className="text-sm text-clay-400">
                    Body Template (paste into Clay)
                  </CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopyBody}
                    className="h-7 px-2 text-clay-500 hover:text-clay-200"
                  >
                    {copied ? (
                      <Check className="h-3.5 w-3.5 text-kiln-teal" />
                    ) : (
                      <Clipboard className="h-3.5 w-3.5" />
                    )}
                    <span className="ml-1.5 text-xs">
                      {copied ? "Copied!" : "Copy"}
                    </span>
                  </Button>
                </CardHeader>
                <CardContent>
                  <pre className="text-xs text-clay-200 bg-clay-950 border border-clay-800 rounded-md p-3 overflow-x-auto font-mono">
                    {JSON.stringify(config.body_template, null, 2)}
                  </pre>
                </CardContent>
              </Card>

              {/* Output columns */}
              {config.expected_output_columns.length > 0 && (
                <Card className="border-clay-800 bg-clay-900">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-clay-400">
                      Expected Output Columns
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow className="border-clay-800 hover:bg-transparent">
                          <TableHead className="text-clay-500">
                            Column
                          </TableHead>
                          <TableHead className="text-clay-500">Type</TableHead>
                          <TableHead className="text-clay-500">
                            Description
                          </TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {config.expected_output_columns.map((col) => (
                          <TableRow key={col.name} className="border-clay-800">
                            <TableCell className="font-mono text-sm text-clay-200">
                              {col.name}
                            </TableCell>
                            <TableCell className="text-sm text-clay-400">
                              {col.type}
                            </TableCell>
                            <TableCell className="text-sm text-clay-400">
                              {col.description}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              )}

              {/* Full config copy */}
              <div className="flex justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopyFull}
                  className="border-clay-700 text-clay-400 hover:text-clay-200"
                >
                  <Clipboard className="h-3.5 w-3.5 mr-1.5" />
                  Copy Full Config JSON
                </Button>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
