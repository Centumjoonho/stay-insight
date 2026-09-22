"use client";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { businessApi } from "@/lib/api/client";

export function OnboardingForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    const body = new FormData(event.currentTarget);
    try {
      await businessApi.onboard(String(body.get("name")));
      router.replace("/properties");
      router.refresh();
    } catch (error) {
      setError(error instanceof Error ? error.message : "사업장을 등록할 수 없습니다.");
      setBusy(false);
    }
  }
  return <form onSubmit={submit} className="mt-6 grid max-w-md gap-4">
    <label>사업장명<input name="name" required maxLength={200} className="field" /></label>
    <button className="action" disabled={busy}>{busy ? "등록 중…" : "사업장 등록"}</button>
    <p role="alert">{error}</p>
  </form>;
}
