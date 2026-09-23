"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { businessApi } from "@/lib/api/client";

export function ExpenseDelete({ organizationId, expenseId }: { organizationId: string; expenseId: string }) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function remove() {
    setBusy(true); setError("");
    try {
      await businessApi.deleteExpense(organizationId, expenseId);
      setConfirming(false); router.refresh();
    } catch (error) {
      setError(error instanceof Error ? error.message : "삭제할 수 없습니다.");
    } finally { setBusy(false); }
  }
  return <div>{confirming ? <div role="group" aria-label="비용 삭제 확인">
    <p>이 직접 입력 비용을 영구 삭제할까요? 복구할 수 없습니다.</p>
    <button type="button" disabled={busy} onClick={remove}>삭제 확인</button>{" "}
    <button type="button" disabled={busy} onClick={() => setConfirming(false)}>취소</button>
  </div> : <button type="button" onClick={() => setConfirming(true)}>삭제</button>}
    <p role="alert">{error}</p></div>;
}
