"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { businessApi } from "@/lib/api/client";
import { capacityError } from "@/lib/inventory";
import { unavailableReasons, type AvailabilityDay, type AvailabilityValues, type CapacityPeriod, type CapacityValues } from "@/lib/api/inventory-types";

export function InventoryManager({ organizationId, propertyId, periods, days, today }: {
  organizationId: string; propertyId: string; periods: CapacityPeriod[]; days: AvailabilityDay[]; today: string;
}) {
  const router = useRouter();
  const [editing, setEditing] = useState<string>();
  const [capacity, setCapacity] = useState<CapacityValues>({ effective_from: today, effective_to: null, inventory_units: 1 });
  const [day, setDay] = useState(today);
  const [unavailable, setUnavailable] = useState<AvailabilityValues>({ unavailable_units: 0, reason: "MAINTENANCE", memo: null });
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<{ kind: "capacity" | "availability"; id: string } | null>(null);
  async function run(action: () => Promise<unknown>, after?: () => void) {
    setBusy(true); setError(""); setStatus("");
    try { await action(); after?.(); setStatus("저장했습니다."); router.refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "요청에 실패했습니다."); }
    finally { setBusy(false); }
  }
  return <div className="space-y-8">
    <p>객실 수 이력이 날짜별 계산의 기준입니다. 빈 구간은 숙소 기본 객실 수로 추정합니다. 판매 제외 기록이 없는 날은 제외 0실로 계산합니다.</p>
    <section aria-labelledby="capacity-title"><h2 id="capacity-title" className="text-xl font-semibold">객실 수 이력</h2>
      <div className="overflow-auto"><table className="my-4 w-full text-left"><caption className="sr-only">등록된 객실 수 이력</caption>
        <thead><tr>{["시작일", "종료일 (포함)", "객실 수", "작업"].map((s) => <th scope="col" key={s}>{s}</th>)}</tr></thead>
        <tbody>{periods.map((p) => <tr key={p.id}><td>{p.effective_from}</td><td>{p.effective_to ?? "종료일 없음"}</td><td>{p.inventory_units}실</td>
          <td><button disabled={busy} className="underline mr-3" onClick={() => { setEditing(p.id); setCapacity(p); setError(""); }}>수정<span className="sr-only"> {p.effective_from} 객실 이력</span></button>
            <button disabled={busy} className="underline" onClick={() => setPendingDelete({ kind: "capacity", id: p.id })}>삭제<span className="sr-only"> {p.effective_from} 객실 이력</span></button></td></tr>)}</tbody>
      </table></div>{!periods.length && <p>등록된 이력이 없습니다.</p>}
      <form aria-label="객실 수 이력 입력" className="grid gap-3" onSubmit={(e) => { e.preventDefault();
        const issue = capacityError(capacity, periods, editing); if (issue) { setError(issue); return; }
        void run(() => businessApi.saveCapacity(organizationId, propertyId, capacity, editing), () => setEditing(undefined));
      }}>
        <fieldset disabled={busy} className="grid gap-3 sm:grid-cols-3"><legend>{editing ? "이력 수정" : "이력 추가"}</legend>
          <label>시작일<input className="field" type="date" min="1901-01-01" max="9998-12-31" required value={capacity.effective_from} onChange={(e) => setCapacity({ ...capacity, effective_from: e.target.value })} /></label>
          <label>종료일 (선택)<input className="field" type="date" min={capacity.effective_from} max="9998-12-31" value={capacity.effective_to ?? ""} onChange={(e) => setCapacity({ ...capacity, effective_to: e.target.value || null })} /></label>
          <label>객실 수<input className="field" type="number" min="1" max="2147483647" step="1" required value={capacity.inventory_units} onChange={(e) => setCapacity({ ...capacity, inventory_units: Number(e.target.value) })} /></label>
          <button className="action">{editing ? "이력 수정 저장" : "이력 추가 저장"}</button>
          {editing && <button type="button" className="underline" onClick={() => { setEditing(undefined); setCapacity({ effective_from: today, effective_to: null, inventory_units: 1 }); }}>수정 취소</button>}
        </fieldset>
      </form>
    </section>
    <section aria-labelledby="availability-title"><h2 id="availability-title" className="text-xl font-semibold">판매 제외 객실</h2>
      <p>예약된 객실이 아니라 정비·소유자 사용 등으로 판매하지 않는 객실을 입력합니다. 같은 날짜 저장은 기존 기록을 대체합니다.</p>
      <form aria-label="판매 제외 입력" className="my-4" onSubmit={(e) => { e.preventDefault(); void run(() => businessApi.saveAvailability(organizationId, propertyId, day, unavailable)); }}>
        <fieldset disabled={busy} className="grid gap-3 sm:grid-cols-2">
          <label>제외 날짜<input className="field" type="date" required min="1901-01-01" max="9998-12-31" value={day} onChange={(e) => setDay(e.target.value)} /></label>
          <label>판매 제외 객실 수<input className="field" type="number" required min="0" step="1" max="2147483647" value={unavailable.unavailable_units} onChange={(e) => setUnavailable({ ...unavailable, unavailable_units: Number(e.target.value) })} /></label>
          <label>사유<select className="field" value={unavailable.reason} onChange={(e) => setUnavailable({ ...unavailable, reason: e.target.value as AvailabilityValues["reason"] })}>{Object.entries(unavailableReasons).map(([key,label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <label>메모 (선택)<input className="field" maxLength={1000} value={unavailable.memo ?? ""} onChange={(e) => setUnavailable({ ...unavailable, memo: e.target.value || null })} /></label>
          <button className="action">판매 제외 저장</button>
        </fieldset>
      </form>
      <form aria-label="가용 객실 조회" className="flex flex-wrap items-end gap-3">
        <label>조회 시작일<input className="field" name="start" type="date" defaultValue={days[0]?.date ?? today} required /></label>
        <label>조회 종료일<input className="field" name="end" type="date" defaultValue={days.at(-1)?.date ?? today} required /></label>
        <button className="action">조회</button><p>최대 366일</p>
      </form>
      <div className="overflow-auto"><table className="my-4 w-full text-left"><caption>날짜별 가용 객실 · 소유자 입력 자료</caption>
        <thead><tr>{["날짜", "기준 객실", "판매 제외", "가용 객실", "사유 / 메모", "작업"].map((s) => <th scope="col" key={s}>{s}</th>)}</tr></thead>
        <tbody>{days.map((d) => <tr key={d.date} className="border-t"><th scope="row">{d.date}</th><td>{d.base_capacity}실{d.capacity_source !== "history" && " (기본값 추정)"}</td>
          <td>{d.unavailable_units}실{!d.override && " (미기록)"}</td><td>{d.available_units}실</td>
          <td>{d.override ? unavailableReasons[d.override.reason] : "—"} {d.override?.memo}</td>
          <td>{d.override && <><button className="underline mr-3" disabled={busy} onClick={() => { setDay(d.date); setUnavailable({ unavailable_units: d.override!.unavailable_units, reason: d.override!.reason, memo: d.override!.memo }); }}>수정<span className="sr-only"> {d.date} 판매 제외</span></button>
            <button className="underline" disabled={busy} onClick={() => setPendingDelete({ kind: "availability", id: d.date })}>삭제<span className="sr-only"> {d.date} 판매 제외</span></button></>}</td></tr>)}</tbody>
      </table></div>
    </section>
    {pendingDelete && <section aria-label="삭제 확인" className="rounded border p-4">
      <p role="alert">{pendingDelete.kind === "capacity" ? "이력을 삭제하면 해당 날짜는 기본 객실 수로 추정될 수 있습니다." : "선택한 날짜의 판매 제외 기록을 삭제합니다."} 삭제할까요?</p>
      <button disabled={busy} className="action mr-3" onClick={() => void run(
        () => pendingDelete.kind === "capacity"
          ? businessApi.deleteCapacity(organizationId, propertyId, pendingDelete.id)
          : businessApi.deleteAvailability(organizationId, propertyId, pendingDelete.id),
        () => { setPendingDelete(null); setEditing(undefined); },
      )}>삭제 확인</button>
      <button disabled={busy} className="underline" onClick={() => setPendingDelete(null)}>삭제 취소</button>
    </section>}
    {error && <p role="alert">{error}</p>}{status && <p role="status">{status}</p>}
  </div>;
}
