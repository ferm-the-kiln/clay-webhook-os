"use client";

import { useEffect, useState } from "react";
import { fetchHealth } from "@/lib/api";

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

  return (
    <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900 px-6 py-4">
      <h2 className="text-xl font-semibold">{title}</h2>
      <div className="flex items-center gap-2 text-sm text-zinc-400">
        <span
          className={`h-2.5 w-2.5 rounded-full ${
            healthy === null
              ? "bg-zinc-600"
              : healthy
                ? "bg-green-500"
                : "bg-red-500"
          }`}
        />
        {healthy === null ? "Checking..." : healthy ? "Connected" : "Offline"}
      </div>
    </header>
  );
}
