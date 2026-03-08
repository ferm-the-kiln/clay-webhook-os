"use client";

import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface BreadcrumbItem {
  id: string;
  name: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  onNavigate: (id: string) => void;
}

export function Breadcrumbs({ items, onNavigate }: BreadcrumbsProps) {
  return (
    <nav className="flex items-center gap-1 text-sm">
      {items.map((item, i) => (
        <div key={item.id} className="flex items-center gap-1">
          {i > 0 && <ChevronRight className="h-3 w-3 text-clay-600" />}
          <button
            onClick={() => onNavigate(item.id)}
            className={cn(
              "rounded px-1.5 py-0.5 transition-colors",
              i === items.length - 1
                ? "text-clay-200 font-medium"
                : "text-clay-500 hover:text-clay-300 hover:bg-clay-800/50"
            )}
          >
            {item.name}
          </button>
        </div>
      ))}
    </nav>
  );
}
