"use client";

import { useEffect, useCallback, useRef } from "react";

export function useBrowserNotification() {
  const permissionRef = useRef<NotificationPermission>("default");

  useEffect(() => {
    if (typeof Notification !== "undefined") {
      permissionRef.current = Notification.permission;
      if (Notification.permission === "default") {
        Notification.requestPermission().then((perm) => {
          permissionRef.current = perm;
        });
      }
    }
  }, []);

  const notify = useCallback((title: string, body: string) => {
    // Only notify if tab is not focused
    if (typeof document === "undefined" || !document.hidden) return;
    if (typeof Notification === "undefined") return;
    if (permissionRef.current !== "granted") return;

    new Notification(title, {
      body,
      icon: "/favicon.ico",
      tag: "clay-execution",
    });
  }, []);

  return { notify };
}
