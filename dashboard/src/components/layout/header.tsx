"use client";

import { useEffect, useState } from "react";
import { fetchHealth, fetchUsageHealth } from "@/lib/api";
import type { HealthResponse, UsageHealth } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Menu, Search, Wifi, WifiOff, Activity, RefreshCw, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { CommandPalette } from "@/components/command-palette";
import { NotificationPanel } from "@/components/notifications/notification-panel";
import { formatTokens, formatNumber } from "@/lib/utils";
import Link from "next/link";

interface Breadcrumb {
  label: string;
  href?: string;
}

interface HeaderProps {
  title: string;
  breadcrumbs?: Breadcrumb[];
  lastUpdated?: Date | null;
  onRefresh?: () => void;
}

function LiveRelativeTime({ date }: { date: Date }) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
  const label =
    diffSec < 5
      ? "just now"
      : diffSec < 60
        ? `${diffSec}s ago`
        : diffSec < 3600
          ? `${Math.floor(diffSec / 60)}m ago`
          : `${Math.floor(diffSec / 3600)}h ago`;
  return <span className="text-xs text-clay-300 font-mono tabular-nums">{label}</span>;
}

const HEALTH_COLORS: Record<string, { dot: string; bg: string; text: string }> = {
  healthy: { dot: "bg-status-success shadow-[0_0_6px_rgba(90,154,106,0.5)]", bg: "bg-status-success/10", text: "text-status-success" },
  warning: { dot: "bg-kiln-mustard shadow-[0_0_6px_rgba(212,168,67,0.5)]", bg: "bg-kiln-mustard/10", text: "text-kiln-mustard" },
  critical: { dot: "bg-kiln-coral shadow-[0_0_6px_rgba(196,90,74,0.5)]", bg: "bg-kiln-coral/10", text: "text-kiln-coral" },
  exhausted: { dot: "bg-kiln-coral shadow-[0_0_6px_rgba(196,90,74,0.5)]", bg: "bg-kiln-coral/10", text: "text-kiln-coral" },
};

export function Header({ title, breadcrumbs, lastUpdated, onRefresh }: HeaderProps) {
  const router = useRouter();
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const [showReconnect, setShowReconnect] = useState(false);
  const [usageHealth, setUsageHealth] = useState<UsageHealth | null>(null);
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let active = true;
    let failCount = 0;
    const check = () => {
      fetchHealth()
        .then((data) => {
          if (active) {
            setHealthy(true);
            setHealthData(data);
            setShowReconnect(false);
            failCount = 0;
          }
        })
        .catch(() => {
          if (active) {
            setHealthy(false);
            setHealthData(null);
            failCount++;
            if (failCount >= 2) setShowReconnect(true);
          }
        });
      fetchUsageHealth()
        .then((h) => active && setUsageHealth(h))
        .catch(() => {});
    };
    check();
    const id = setInterval(check, 10000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const usageColors = usageHealth
    ? HEALTH_COLORS[usageHealth.status] || HEALTH_COLORS.healthy
    : null;
  const showUsageBanner =
    usageHealth &&
    (usageHealth.status === "warning" ||
      usageHealth.status === "critical" ||
      usageHealth.status === "exhausted");

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
      {showUsageBanner && usageColors && (
        <div className={`flex items-center justify-center gap-2 ${usageColors.bg} border-b border-current/10 px-4 py-2 text-sm ${usageColors.text}`}>
          <Activity className="h-4 w-4" />
          <span>
            {usageHealth!.status === "exhausted"
              ? "Subscription quota exhausted — jobs will fail until reset."
              : usageHealth!.status === "critical"
                ? "Subscription nearing limit — throttle usage."
                : `Subscription usage elevated — ${formatTokens(usageHealth!.today_tokens)} tokens today.`}
          </span>
        </div>
      )}
      <header className="flex items-center justify-between border-b border-clay-600 bg-clay-850/80 backdrop-blur-sm px-4 md:px-6 py-4">
        <div className="flex items-center gap-3">
          {/* Hamburger menu for mobile */}
          <Button
            variant="ghost"
            size="icon-sm"
            className="md:hidden text-clay-200 hover:text-clay-100"
            onClick={() =>
              document.dispatchEvent(new CustomEvent("toggle-mobile-sidebar"))
            }
            aria-label="Open navigation menu"
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-semibold font-[family-name:var(--font-sans)] text-clay-100">
              {title}
            </h2>
            {breadcrumbs && breadcrumbs.length > 0 && (
              <div className="hidden sm:flex items-center gap-1.5 text-sm font-mono">
                {breadcrumbs.map((crumb, i) => (
                  <span key={i} className="flex items-center gap-1.5">
                    <span className="text-clay-300">/</span>
                    {crumb.href ? (
                      <Link href={crumb.href} className="text-clay-300 hover:text-kiln-teal transition-colors duration-150">
                        {crumb.label}
                      </Link>
                    ) : (
                      <span className="text-clay-200">{crumb.label}</span>
                    )}
                  </span>
                ))}
              </div>
            )}
          </div>
          {lastUpdated && (
            <div className="hidden sm:flex items-center gap-1.5 ml-3">
              <LiveRelativeTime date={lastUpdated} />
              {onRefresh && (
                <button
                  onClick={onRefresh}
                  className="text-clay-300 hover:text-clay-100 transition-colors duration-150"
                  aria-label="Refresh"
                >
                  <RefreshCw className="h-3 w-3" />
                </button>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button
            className="hidden md:flex items-center gap-2 rounded-md border border-clay-500 bg-clay-900 px-3 py-1.5 text-xs text-clay-300 shadow-[inset_0_1px_3px_rgba(0,0,0,0.4)] hover:border-clay-400 hover:text-clay-200 transition-colors duration-150"
            onClick={() => {
              document.dispatchEvent(
                new KeyboardEvent("keydown", { key: "k", metaKey: true })
              );
            }}
          >
            <Search className="h-3.5 w-3.5" />
            <span>Search...</span>
            <kbd className="retro-keycap">
              {"\u2318"}K
            </kbd>
          </button>

          {/* Subscription health indicator */}
          {usageHealth && usageColors && (
            <Tooltip>
              <TooltipTrigger asChild>
                <button className={`hidden sm:flex items-center gap-1.5 rounded-md px-2 py-1 text-xs ${usageColors.bg} ${usageColors.text} transition-colors duration-150`}>
                  <span className={`h-2 w-2 rounded-full ${usageColors.dot}`} />
                  <span className="hidden md:inline font-mono tabular-nums">
                    {formatTokens(usageHealth.today_tokens)}
                  </span>
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                <p className="font-medium mb-1">Subscription: {usageHealth.status}</p>
                <p className="font-mono tabular-nums">{formatTokens(usageHealth.today_tokens)} tokens today</p>
                <p className="font-mono tabular-nums">{formatNumber(usageHealth.today_requests)} requests today</p>
                {usageHealth.today_errors > 0 && (
                  <p className="text-kiln-coral">{usageHealth.today_errors} errors today</p>
                )}
                <p className="text-clay-300 mt-1">Press <kbd className="retro-keycap">?</kbd> for shortcuts</p>
              </TooltipContent>
            </Tooltip>
          )}

          <NotificationPanel />

          <Tooltip>
            <TooltipTrigger asChild>
              <div role="status" aria-live="polite">
                <Badge
                  variant={
                    healthy === null ? "secondary" : healthy ? "default" : "destructive"
                  }
                  className={`cursor-default ${
                    healthy === true
                      ? "bg-status-success/15 text-status-success border-status-success/25 hover:bg-status-success/20"
                      : healthy === false
                        ? "bg-kiln-coral/15 text-kiln-coral border-kiln-coral/25"
                        : ""
                  }`}
                >
                  {healthy === true ? (
                    <Wifi className="h-3 w-3 mr-1" />
                  ) : healthy === false ? (
                    <WifiOff className="h-3 w-3 mr-1" />
                  ) : (
                    <span className="mr-1.5 h-2 w-2 rounded-full bg-clay-400 animate-pulse" />
                  )}
                  {healthy === null ? "Checking..." : healthy ? "Connected" : "Offline"}
                </Badge>
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-xs">
              {healthData?.claude_user?.logged_in ? (
                <div className="space-y-1">
                  <p className="font-medium">
                    {healthData.claude_user.email || "Claude Code"}
                  </p>
                  <p className="text-clay-300 text-xs">
                    Subscription: {healthData.claude_user.subscription_type || "unknown"}
                  </p>
                  {healthData.backend_host && (
                    <p className="text-clay-300 text-xs">
                      Host: {healthData.backend_host}
                    </p>
                  )}
                  {healthData.daemon && (
                    <p className={`text-xs ${healthData.daemon.running ? "text-status-success" : "text-kiln-coral"}`}>
                      Daemon: {healthData.daemon.running ? "running" : "stopped"}
                    </p>
                  )}
                </div>
              ) : healthy === false ? (
                <p>Backend unreachable. Is the server running?</p>
              ) : (
                <p>Checking connection...</p>
              )}
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                className="text-clay-400 hover:text-clay-100"
                onClick={async () => {
                  const supabase = createClient();
                  await supabase.auth.signOut();
                  router.push("/login");
                  router.refresh();
                }}
                aria-label="Sign out"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">Sign out</TooltipContent>
          </Tooltip>
        </div>
      </header>
      <CommandPalette />
    </>
  );
}
