"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sparkles } from "lucide-react";
import { fetchClients } from "@/lib/api";
import type { ClientSummary } from "@/lib/types";
import type { PrepInputs } from "@/lib/prep-types";

interface PrepInputFormProps {
  onSubmit: (inputs: PrepInputs) => void;
  disabled: boolean;
}

export function PrepInputForm({ onSubmit, disabled }: PrepInputFormProps) {
  const [companyName, setCompanyName] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactTitle, setContactTitle] = useState("");
  const [clientSlug, setClientSlug] = useState("");
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [clientsLoading, setClientsLoading] = useState(true);

  useEffect(() => {
    fetchClients()
      .then((r) => setClients(r.clients))
      .catch(() => {})
      .finally(() => setClientsLoading(false));
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim()) return;
    onSubmit({
      companyName: companyName.trim(),
      contactName: contactName.trim(),
      contactTitle: contactTitle.trim(),
      clientSlug,
    });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-lg mx-auto space-y-4"
    >
      <div className="text-center mb-6">
        <h2 className="text-lg font-semibold text-clay-100 mb-1">
          Prepare for a call
        </h2>
        <p className="text-sm text-clay-300">
          Enter the company and contact details to generate a complete call
          brief.
        </p>
      </div>

      {/* Company name — required */}
      <div className="space-y-1.5">
        <label htmlFor="company" className="text-xs text-clay-200">
          Company name <span className="text-red-400">*</span>
        </label>
        <Input
          id="company"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          placeholder="e.g. Acme Corp"
          className="bg-clay-700/50 border-clay-500 text-clay-100 placeholder:text-clay-300"
          disabled={disabled}
          autoFocus
        />
      </div>

      {/* Contact name — optional */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <label htmlFor="contact" className="text-xs text-clay-200">
            Contact name
          </label>
          <Input
            id="contact"
            value={contactName}
            onChange={(e) => setContactName(e.target.value)}
            placeholder="e.g. Jane Smith"
            className="bg-clay-700/50 border-clay-500 text-clay-100 placeholder:text-clay-300"
            disabled={disabled}
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="title" className="text-xs text-clay-200">
            Title
          </label>
          <Input
            id="title"
            value={contactTitle}
            onChange={(e) => setContactTitle(e.target.value)}
            placeholder="e.g. VP of Sales"
            className="bg-clay-700/50 border-clay-500 text-clay-100 placeholder:text-clay-300"
            disabled={disabled}
          />
        </div>
      </div>

      {/* Client slug — optional */}
      <div className="space-y-1.5">
        <label htmlFor="client" className="text-xs text-clay-200">
          Client context{" "}
          <span className="text-clay-300 font-normal">
            (better results with context)
          </span>
        </label>
        <Select value={clientSlug} onValueChange={setClientSlug} disabled={disabled}>
          <SelectTrigger className="bg-clay-700/50 border-clay-500 text-clay-100">
            <SelectValue placeholder={clientsLoading ? "Loading clients..." : "Select a client (optional)"} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">No client context</SelectItem>
            {clients.map((c) => (
              <SelectItem key={c.slug} value={c.slug}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Button
        type="submit"
        disabled={!companyName.trim() || disabled}
        className="w-full h-10 bg-kiln-teal hover:bg-kiln-teal/90 text-clay-900 font-medium"
      >
        <Sparkles className="h-4 w-4 mr-2" />
        Prepare Brief
      </Button>
    </form>
  );
}
