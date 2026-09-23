"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { businessApi } from "@/lib/api/client";
import { expenseCategories, costTypes, type Expense } from "@/lib/api/expense-types";
import { expenseFormValues } from "@/lib/expenses";

export function ExpenseForm({ organizationId, propertyId, today, expense }: {
  organizationId: string; propertyId: string; today: string; expense?: Expense;
}) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    try {
      const body = expenseFormValues(new FormData(event.currentTarget));
      setBusy(true);
      if (expense) await businessApi.updateExpense(organizationId, expense.id, body);
      else await businessApi.createExpense(organizationId, { ...body, property_id: propertyId });
      // Show the saved expense even when its date is outside the current month.
      router.replace(`/properties/${propertyId}/expenses?from=${body.expense_date}&to=${body.expense_date}`);
      router.refresh();
    } catch (error) {
      setError(error instanceof Error ? error.message : "비용을 저장할 수 없습니다.");
      setBusy(false);
    }
  }
  return <form onSubmit={submit} className="mt-6 grid max-w-lg gap-4">
    <p>직접 입력 비용 · 플랫폼 수수료는 예약 CSV에서 집계됩니다. 이곳에 중복 입력하지 마세요.</p>
    <fieldset disabled={busy} className="grid gap-4">
      <label>비용 발생일<input className="field" type="date" name="expense_date" defaultValue={expense?.expense_date ?? today} required /></label>
      <label>비용 항목<select className="field" name="category" defaultValue={expense?.category ?? ""} required>
        <option value="" disabled>선택해 주세요</option>{Object.entries(expenseCategories).map(([key, label]) =>
          <option key={key} value={key}>{label}</option>)}</select></label>
      <label>고정비 / 변동비<select className="field" name="cost_type" defaultValue={expense?.cost_type ?? ""} required>
        <option value="" disabled>직접 선택해 주세요</option>{Object.entries(costTypes).map(([key, label]) =>
          <option key={key} value={key}>{label}</option>)}</select></label>
      <label>금액 (원)<input className="field" name="amount" inputMode="numeric" pattern="[0-9]{1,18}" maxLength={18} defaultValue={expense?.amount ?? ""} required /></label>
      <label>메모<textarea className="field" name="memo" maxLength={1000} defaultValue={expense?.memo ?? ""} /></label>
      <button className="action" disabled={busy}>{busy ? "저장 중…" : expense ? "수정 저장" : "비용 등록"}</button>
    </fieldset>
    <p role="alert">{error}</p><Link href={`/properties/${propertyId}/expenses`}>비용 목록</Link>
  </form>;
}
