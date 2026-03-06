"use client";

import { useState, useEffect } from "react";
import type { Destination, DestinationType } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface DestinationFormProps {
  initial?: Destination | null;
  onSubmit: (data: {
    name: string;
    type: DestinationType;
    url: string;
    auth_header_name: string;
    auth_header_value: string;
    client_slug: string | null;
  }) => void;
  loading?: boolean;
}

export function DestinationForm({ initial, onSubmit, loading }: DestinationFormProps) {
  const [name, setName] = useState(initial?.name ?? "");
  const [type, setType] = useState<DestinationType>(initial?.type ?? "clay_webhook");
  const [url, setUrl] = useState(initial?.url ?? "");
  const [authName, setAuthName] = useState(initial?.auth_header_name ?? "");
  const [authValue, setAuthValue] = useState(initial?.auth_header_value ?? "");
  const [clientSlug, setClientSlug] = useState(initial?.client_slug ?? "");

  useEffect(() => {
    if (!initial && type === "clay_webhook" && !authName) {
      setAuthName("x-clay-webhook-auth");
    }
  }, [type, initial, authName]);

  const handleTypeChange = (val: string) => {
    const newType = val as DestinationType;
    setType(newType);
    if (newType === "clay_webhook" && !authName) {
      setAuthName("x-clay-webhook-auth");
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
          Name
        </label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Twelve Labs - ICP Scores"
          className="border-clay-700 bg-clay-900 text-clay-200"
        />
      </div>

      <div>
        <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
          Type
        </label>
        <Select value={type} onValueChange={handleTypeChange}>
          <SelectTrigger className="w-full border-clay-700 bg-clay-900 text-clay-200">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="border-clay-700 bg-clay-900">
            <SelectItem value="clay_webhook">Clay Webhook</SelectItem>
            <SelectItem value="generic_webhook">Generic Webhook</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
          URL
        </label>
        <Input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://..."
          className="border-clay-700 bg-clay-900 text-clay-200"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
            Auth Header Name
          </label>
          <Input
            value={authName}
            onChange={(e) => setAuthName(e.target.value)}
            placeholder="x-api-key"
            className="border-clay-700 bg-clay-900 text-clay-200"
          />
        </div>
        <div>
          <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
            Auth Header Value
          </label>
          <Input
            type="password"
            value={authValue}
            onChange={(e) => setAuthValue(e.target.value)}
            placeholder="secret token"
            className="border-clay-700 bg-clay-900 text-clay-200"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5">
          Client Slug (optional)
        </label>
        <Input
          value={clientSlug}
          onChange={(e) => setClientSlug(e.target.value)}
          placeholder="twelve-labs"
          className="border-clay-700 bg-clay-900 text-clay-200"
        />
      </div>

      <Button
        onClick={() =>
          onSubmit({
            name,
            type,
            url,
            auth_header_name: authName,
            auth_header_value: authValue,
            client_slug: clientSlug || null,
          })
        }
        disabled={!name || !url || loading}
        className="w-full bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
      >
        {loading ? "Saving..." : initial ? "Update Destination" : "Create Destination"}
      </Button>
    </div>
  );
}
