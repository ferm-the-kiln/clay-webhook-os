"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Play, FlaskConical, X } from "lucide-react";
import type { FunctionInput } from "@/lib/types";

interface FunctionPlaygroundProps {
  inputs: FunctionInput[];
  testInputs: Record<string, string>;
  setTestInputs: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  testResult: Record<string, unknown> | null;
  testing: boolean;
  onRun: () => void;
  onClose: () => void;
}

export function FunctionPlayground({
  inputs,
  testInputs,
  setTestInputs,
  testResult,
  testing,
  onRun,
  onClose,
}: FunctionPlaygroundProps) {
  return (
    <Card className="border-clay-600 border-kiln-teal/30">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm text-clay-200 flex items-center gap-2">
            <FlaskConical className="h-4 w-4 text-kiln-teal" />
            Quick Test
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-clay-400 h-6 w-6 p-0"
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {inputs.length === 0 ? (
          <div className="text-xs text-clay-500">
            No inputs defined — will run with empty data.
          </div>
        ) : (
          <div className="space-y-2">
            {inputs.map((inp) => (
              <div key={inp.name}>
                <label className="text-[10px] text-clay-400 mb-0.5 block">
                  {inp.name}{" "}
                  <span className="text-clay-600">({inp.type})</span>
                  {inp.required && (
                    <span className="text-red-400 ml-1">*</span>
                  )}
                </label>
                <Input
                  value={testInputs[inp.name] || ""}
                  onChange={(e) =>
                    setTestInputs((prev) => ({
                      ...prev,
                      [inp.name]: e.target.value,
                    }))
                  }
                  placeholder={`Enter ${inp.name}...`}
                  className="bg-clay-900 border-clay-600 text-clay-100 text-xs h-7"
                />
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={onRun}
            disabled={testing}
            className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light"
          >
            <Play className="h-3 w-3 mr-1" />
            {testing ? "Running..." : "Run"}
          </Button>
          {testResult && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setTestInputs({});
              }}
              className="text-clay-400 text-xs"
            >
              Clear
            </Button>
          )}
          <span className="text-[10px] text-clay-500 ml-auto">
            <kbd className="px-1 py-0.5 rounded bg-clay-800 border border-clay-600 text-[9px]">
              {"\u2318"}+Enter
            </kbd>{" "}
            to run
          </span>
        </div>

        {testResult && (
          <pre className="text-[11px] text-clay-300 bg-clay-900 p-3 rounded border border-clay-700 overflow-auto max-h-64 whitespace-pre-wrap">
            {JSON.stringify(testResult, null, 2)}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}
