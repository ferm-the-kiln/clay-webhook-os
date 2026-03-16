"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SequenceLabRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/pipeline/sequence-lab");
  }, [router]);
  return null;
}
