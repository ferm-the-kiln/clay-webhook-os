"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { fetchHealth } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

const PAGE_ASSETS: Record<string, string> = {
  Dashboard: "/brand-assets/v2-dashboard.png",
  Playground: "/brand-assets/v2-playground.png",
  "Batch Processing": "/brand-assets/v2-batch.png",
};

export function Header({ title }: { title: string }) {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    const check = () =>
      fetchHealth()
        .then(() => active && setHealthy(true))
        .catch(() => active && setHealthy(false));
    check();
    const id = setInterval(check, 10000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const asset = PAGE_ASSETS[title];

  return (
    <header className="flex items-center justify-between border-b border-clay-800 bg-clay-900/80 backdrop-blur-sm px-6 py-4">
      <div className="flex items-center gap-3">
        {asset && (
          <Image
            src={asset}
            alt=""
            width={28}
            height={28}
            className="rounded-sm"
          />
        )}
        <h2 className="text-xl font-semibold font-[family-name:var(--font-sans)] text-kiln-cream">
          {title}
        </h2>
      </div>
      <Badge
        variant={
          healthy === null ? "secondary" : healthy ? "default" : "destructive"
        }
        className={
          healthy === true
            ? "bg-kiln-teal/15 text-kiln-teal border-kiln-teal/30 hover:bg-kiln-teal/20"
            : healthy === false
              ? "bg-kiln-coral/15 text-kiln-coral border-kiln-coral/30"
              : ""
        }
      >
        <span
          className={`mr-1.5 h-2 w-2 rounded-full ${
            healthy === null
              ? "bg-clay-500"
              : healthy
                ? "bg-kiln-teal animate-pulse"
                : "bg-kiln-coral"
          }`}
        />
        {healthy === null ? "Checking..." : healthy ? "Connected" : "Offline"}
      </Badge>
    </header>
  );
}
