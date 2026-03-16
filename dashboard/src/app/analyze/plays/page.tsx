"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PlaysRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/pipeline/plays");
  }, [router]);
  return null;
}
