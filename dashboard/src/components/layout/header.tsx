"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { fetchHealth } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Menu, Search, Wifi, WifiOff } from "lucide-react";
import { CommandPalette } from "@/components/command-palette";

const PAGE_ASSETS: Record<string, string> = {
  Dashboard: "/brand-assets/v2-dashboard.png",
  Playground: "/brand-assets/v2-playground.png",
  "Batch Processing": "/brand-assets/v2-batch.png",
  Settings: "",
};

export function Header({ title }: { title: string }) {
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const [showReconnect, setShowReconnect] = useState(false);

  useEffect(() => {
    let active = true;
    let failCount = 0;
    const check = () =>
      fetchHealth()
        .then(() => {
          if (active) {
            setHealthy(true);
            setShowReconnect(false);
            failCount = 0;
          }
        })
        .catch(() => {
          if (active) {
            setHealthy(false);
            failCount++;
            if (failCount >= 2) setShowReconnect(true);
          }
        });
    check();
    const id = setInterval(check, 10000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const asset = PAGE_ASSETS[title];

  return (
    <>
      {showReconnect && (
        <div className="flex items-center justify-center gap-2 bg-kiln-coral/10 border-b border-kiln-coral/20 px-4 py-2 text-sm text-kiln-coral">
          <WifiOff className="h-4 w-4" />
          <span>Connection lost</span>
          <Button
            variant="outline"
            size="xs"
            onClick={() => {
              setShowReconnect(false);
              fetchHealth()
                .then(() => setHealthy(true))
                .catch(() => {
                  setHealthy(false);
                  setShowReconnect(true);
                });
            }}
            className="border-kiln-coral/30 text-kiln-coral hover:bg-kiln-coral/10 ml-2"
          >
            Reconnect
          </Button>
        </div>
      )}
      <header className="flex items-center justify-between border-b border-clay-800 bg-clay-900/80 backdrop-blur-sm px-4 md:px-6 py-4">
        <div className="flex items-center gap-3">
          {/* Hamburger menu for mobile */}
          <Button
            variant="ghost"
            size="icon-sm"
            className="md:hidden text-clay-400 hover:text-clay-200"
            onClick={() =>
              document.dispatchEvent(new CustomEvent("toggle-mobile-sidebar"))
            }
            aria-label="Open navigation menu"
          >
            <Menu className="h-5 w-5" />
          </Button>
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
        <div className="flex items-center gap-3">
          <button
            className="hidden md:flex items-center gap-2 rounded-lg border border-clay-700 bg-clay-900 px-3 py-1.5 text-xs text-clay-500 hover:border-clay-600 hover:text-clay-400 transition-colors"
            onClick={() => {
              document.dispatchEvent(
                new KeyboardEvent("keydown", { key: "k", metaKey: true })
              );
            }}
          >
            <Search className="h-3.5 w-3.5" />
            <span>Search...</span>
            <kbd className="rounded border border-clay-700 bg-clay-800 px-1.5 py-0.5 font-mono text-[10px] text-clay-400">
              {"\u2318"}K
            </kbd>
          </button>
          <div role="status" aria-live="polite">
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
              {healthy === true ? (
                <Wifi className="h-3 w-3 mr-1" />
              ) : healthy === false ? (
                <WifiOff className="h-3 w-3 mr-1" />
              ) : (
                <span className="mr-1.5 h-2 w-2 rounded-full bg-clay-500" />
              )}
              {healthy === null ? "Checking..." : healthy ? "Connected" : "Offline"}
            </Badge>
          </div>
        </div>
      </header>
      <CommandPalette />
    </>
  );
}
