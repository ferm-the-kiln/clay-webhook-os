"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Bell, X, CheckCheck, AlertTriangle, Zap } from "lucide-react";
import { createJobStream } from "@/lib/api";
import { formatRelativeTime } from "@/lib/utils";

interface Notification {
  id: string;
  type: "job_failed" | "job_completed" | "warning";
  title: string;
  message: string;
  timestamp: number;
  read: boolean;
}

const MAX_NOTIFICATIONS = 50;

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const esRef = useRef<EventSource | null>(null);

  const addNotification = useCallback(
    (n: Omit<Notification, "id" | "read">) => {
      setNotifications((prev) => {
        const next = [
          { ...n, id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, read: false },
          ...prev,
        ];
        return next.slice(0, MAX_NOTIFICATIONS);
      });
    },
    []
  );

  useEffect(() => {
    try {
      const es = createJobStream((eventType, data) => {
        if (eventType === "job_updated") {
          const d = data as { id?: string; skill?: string; status?: string; error?: string };
          if (d.status === "failed" || d.status === "dead_letter") {
            addNotification({
              type: "job_failed",
              title: `Job failed: ${d.skill || "unknown"}`,
              message: (d.error as string) || `Job ${(d.id as string)?.slice(0, 8)} failed`,
              timestamp: Date.now() / 1000,
            });
          }
        }
      });
      esRef.current = es;
      es.onerror = () => {
        es.close();
        esRef.current = null;
      };
    } catch {
      // SSE not available
    }

    return () => {
      if (esRef.current) esRef.current.close();
    };
  }, [addNotification]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  return { notifications, unreadCount, markAllRead, clearAll };
}

export function NotificationPanel() {
  const [open, setOpen] = useState(false);
  const { notifications, unreadCount, markAllRead, clearAll } =
    useNotifications();

  return (
    <>
      <button
        onClick={() => {
          setOpen(true);
          markAllRead();
        }}
        className="relative p-1.5 rounded-md text-clay-400 hover:text-clay-200 hover:bg-clay-800 transition-colors"
        aria-label="Notifications"
      >
        <Bell className="h-4.5 w-4.5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-kiln-coral text-[10px] font-bold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent
          side="right"
          className="w-full sm:max-w-sm bg-clay-900 border-clay-800"
        >
          <SheetHeader>
            <div className="flex items-center justify-between">
              <SheetTitle className="text-clay-100">Notifications</SheetTitle>
              <div className="flex items-center gap-2">
                {notifications.length > 0 && (
                  <>
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={markAllRead}
                      className="text-clay-500 hover:text-clay-300 text-xs"
                    >
                      <CheckCheck className="h-3 w-3 mr-1" />
                      Mark read
                    </Button>
                    <Button
                      variant="ghost"
                      size="xs"
                      onClick={clearAll}
                      className="text-clay-500 hover:text-clay-300 text-xs"
                    >
                      <X className="h-3 w-3 mr-1" />
                      Clear
                    </Button>
                  </>
                )}
              </div>
            </div>
            <SheetDescription className="sr-only">
              Recent notifications
            </SheetDescription>
          </SheetHeader>
          <div className="mt-4 space-y-1 max-h-[calc(100vh-120px)] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="py-12 text-center">
                <Bell className="h-8 w-8 text-clay-700 mx-auto mb-3" />
                <p className="text-sm text-clay-500">No notifications yet</p>
                <p className="text-xs text-clay-600 mt-1">
                  Job failures will appear here
                </p>
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={`flex items-start gap-3 rounded-lg px-3 py-2.5 transition-colors ${
                    n.read ? "opacity-60" : "bg-clay-800/50"
                  }`}
                >
                  <div className="shrink-0 mt-0.5">
                    {n.type === "job_failed" ? (
                      <AlertTriangle className="h-4 w-4 text-kiln-coral" />
                    ) : (
                      <Zap className="h-4 w-4 text-kiln-teal" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-clay-200 font-medium truncate">
                      {n.title}
                    </p>
                    <p className="text-xs text-clay-500 truncate">{n.message}</p>
                    <p className="text-xs text-clay-600 mt-0.5">
                      {formatRelativeTime(n.timestamp)}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
