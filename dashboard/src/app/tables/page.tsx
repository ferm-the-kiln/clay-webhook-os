"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Plus, Table2, Upload, Trash2, MoreVertical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { fetchTables, createTable, deleteTable, importTableCsv } from "@/lib/api";
import type { TableSummary } from "@/lib/types";
import Papa from "papaparse";

export default function TablesPage() {
  const router = useRouter();
  const [tables, setTables] = useState<TableSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchTables()
      .then((r) => setTables(r.tables))
      .catch(() => toast.error("Failed to load tables"))
      .finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    try {
      const table = await createTable({ name: "Untitled Table" });
      router.push(`/tables/${table.id}`);
    } catch {
      toast.error("Failed to create table");
    }
  };

  const handleImportCsv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      // Create table from filename
      const name = file.name.replace(/\.csv$/i, "").replace(/[_-]/g, " ");
      const table = await createTable({ name });
      await importTableCsv(table.id, file);
      toast.success(`Imported ${name}`);
      router.push(`/tables/${table.id}`);
    } catch {
      toast.error("Failed to import CSV");
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteTable(id);
      setTables((prev) => prev.filter((t) => t.id !== id));
      toast.success("Table deleted");
    } catch {
      toast.error("Failed to delete table");
    }
  };

  const formatDate = (ts: number) =>
    new Date(ts * 1000).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-2">
              <Table2 className="w-6 h-6 text-kiln-teal" />
              Tables
            </h1>
            <p className="text-zinc-400 text-sm mt-1">
              Clay-style enrichment tables. Import data, add columns, watch results fill in.
            </p>
          </div>
          <div className="flex gap-2">
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={handleImportCsv}
            />
            <Button
              variant="outline"
              className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
              onClick={() => fileRef.current?.click()}
            >
              <Upload className="w-4 h-4 mr-2" />
              Import CSV
            </Button>
            <Button
              className="bg-kiln-teal text-black hover:bg-kiln-teal/90"
              onClick={handleCreate}
            >
              <Plus className="w-4 h-4 mr-2" />
              New Table
            </Button>
          </div>
        </div>

        {/* Table Grid */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-32 rounded-lg bg-zinc-900 border border-zinc-800 animate-pulse"
              />
            ))}
          </div>
        ) : tables.length === 0 ? (
          <div className="text-center py-20">
            <Table2 className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
            <p className="text-zinc-400 text-lg mb-2">No tables yet</p>
            <p className="text-zinc-600 text-sm mb-6">
              Create a new table or import a CSV to get started
            </p>
            <div className="flex gap-2 justify-center">
              <Button
                variant="outline"
                className="border-zinc-700 text-zinc-300"
                onClick={() => fileRef.current?.click()}
              >
                <Upload className="w-4 h-4 mr-2" />
                Import CSV
              </Button>
              <Button
                className="bg-kiln-teal text-black"
                onClick={handleCreate}
              >
                <Plus className="w-4 h-4 mr-2" />
                New Table
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {tables.map((t) => (
              <div
                key={t.id}
                className="group rounded-lg bg-zinc-900 border border-zinc-800 hover:border-zinc-600 transition-colors cursor-pointer p-4"
                onClick={() => router.push(`/tables/${t.id}`)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-white truncate">{t.name}</h3>
                    {t.description && (
                      <p className="text-zinc-500 text-sm mt-1 truncate">{t.description}</p>
                    )}
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 opacity-0 group-hover:opacity-100 text-zinc-400"
                      >
                        <MoreVertical className="w-4 h-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="bg-zinc-900 border-zinc-700">
                      <DropdownMenuItem
                        className="text-red-400 focus:text-red-400"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(t.id);
                        }}
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                <div className="flex items-center gap-4 mt-4 text-xs text-zinc-500">
                  <span>{t.row_count} rows</span>
                  <span>{t.column_count} columns</span>
                  <span className="ml-auto">{formatDate(t.updated_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
