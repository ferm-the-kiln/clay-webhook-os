"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ScoringRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/pipeline/score");
  }, [router]);
  return null;
}
