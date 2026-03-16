"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function EmailLabRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/pipeline/email-lab");
  }, [router]);
  return null;
}
