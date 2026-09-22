"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { browserAuth } from "@/lib/supabase/client";

export function SignOut() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function signOut() {
    setBusy(true);
    try {
      const result = await browserAuth().auth.signOut();
      if (result.error) throw result.error;
      router.replace("/login");
      router.refresh();
    } catch {
      setError("로그아웃하지 못했습니다. 다시 시도해 주세요.");
      setBusy(false);
    }
  }
  return <div><button onClick={signOut} disabled={busy} className="underline">로그아웃</button>
    <p role="alert">{error}</p></div>;
}
