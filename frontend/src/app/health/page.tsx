"use client";

import { useEffect, useState } from "react";
import { checkBackendHealth } from "@/lib/health";

type Status = "checking" | "backend connected" | "backend unavailable";

export default function HealthPage() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const timeout = window.setTimeout(() => controller.abort(), 5000);

    void checkBackendHealth(process.env.NEXT_PUBLIC_API_BASE_URL, controller.signal)
      .then((connected) => {
        if (active) setStatus(connected ? "backend connected" : "backend unavailable");
      })
      .finally(() => window.clearTimeout(timeout));

    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, []);

  return (
    <section>
      <h1 className="text-3xl font-semibold">백엔드 연결 상태</h1>
      <p className="mt-4 text-slate-600">FastAPI 서버의 응답을 확인합니다.</p>
      <p role="status" aria-live="polite" className="mt-8 rounded-lg border border-slate-200 bg-white p-6 font-mono text-lg">
        {status}
      </p>
    </section>
  );
}
