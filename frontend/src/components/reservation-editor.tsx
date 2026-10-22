"use client";
import Link from "next/link";
import { Button, DataQualityNotice, FieldGroup, FormField, SectionHeader, Surface, buttonClass } from "@/components/ui";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { businessApi } from "@/lib/api/client";
import { ApiError } from "@/lib/api/transport";
import { channels, type Reservation } from "@/lib/api/import-types";
import { reservationFields, reservationValues, changedReservationValues, type AuditEvent, type ReservationField } from "@/lib/reservations";

export function ReservationHistory({ items, total, offset = 0 }: { items: AuditEvent[]; total: number; offset?: number }) {
  const kinds: Record<string,string> = {MANUAL_CREATE:"직접 등록",MANUAL_UPDATE:"수동 수정",STATUS_CHANGE:"상태 변경",MANUAL_OVERRIDE_RELEASED:"CSV 보호 해제",CSV_UPDATE:"CSV 갱신"};
  const value = (field: string, raw: unknown) => {
    if (raw === null || raw === undefined) return "미입력";
    if (raw === "MANUAL_PROTECTED") return "수동 보호";
    if (raw === "CSV_MANAGED") return "CSV 갱신 허용";
    if (field === "gross_revenue" || field === "channel_fee") return BigInt(String(raw)).toLocaleString("ko-KR") + "원";
    return ({CONFIRMED:"확정",CANCELLED:"취소",UNKNOWN:"미확인"} as Record<string,string>)[String(raw)] ?? String(raw);
  };
  return <section id="reservation-history" className="grid gap-4"><h2 className="text-xl font-semibold">변경 이력</h2>
    <p>변경 이력은 Phase 12 도입 이후부터 제공합니다. 총 {total}건</p>
    <ol className="audit-list">{items.map((item) => <li className="surface audit-event" key={item.id}>
      <p><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString("ko-KR",{timeZone:"Asia/Seoul"})}</time> · {kinds[item.event_type]} · {item.change_source === "MANUAL" ? "수동" : "CSV"} · 사용자 {item.actor_subject.slice(0,8)}</p>
      <p className="my-3 text-sm">사유: {item.reason ?? "해당 없음"}</p>
      <table className="data-table"><caption className="sr-only">변경 전후 값</caption><thead><tr><th scope="col">항목</th><th scope="col">변경 전</th><th scope="col">변경 후</th></tr></thead>
        <tbody>{item.changed_fields.map((field) => <tr key={field}><th scope="row">{reservationFields[field as ReservationField] ?? field}</th><td>{value(field,item.before_values[field])}</td><td>{value(field,item.after_values[field])}</td></tr>)}</tbody></table>
    </li>)}</ol><nav className="form-actions" aria-label="변경 이력 페이지">{offset > 0 && <Link href={`?history_offset=${Math.max(0,offset-50)}`}>이전 이력</Link>}{offset+items.length < total && <Link href={`?history_offset=${offset+50}`}>다음 이력</Link>}</nav>
  </section>;
}

export function ReservationEditor({ organizationId, propertyId, reservation, history = [], historyTotal = 0, historyOffset = 0 }: {
  organizationId: string; propertyId: string; reservation?: Reservation; history?: AuditEvent[]; historyTotal?: number; historyOffset?: number;
}) {
  const router = useRouter();
  const [error,setError] = useState(""), [busy,setBusy] = useState(false), [conflict,setConflict] = useState(false);
  const [releaseField,setReleaseField] = useState<ReservationField | null>(null);
  const protectedFields = reservation?.manual_protected_fields ?? [];
  async function run(action: () => Promise<Reservation>) {
    setBusy(true);setError("");
    try { const saved = await action(); router.replace(`/properties/${propertyId}/reservations/${saved.id}`);router.refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "예약을 저장할 수 없습니다."); if (e instanceof ApiError && e.status === 409) setConflict(true); }
    finally {setBusy(false);}
  }
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); const form = new FormData(e.currentTarget);setError("");
    try {
      const values = reservationValues(form);
      if (reservation) {
        const change_reason = String(form.get("change_reason") ?? "").trim();
        if (!change_reason) throw new Error("변경 사유를 입력해 주세요.");
        const changed = changedReservationValues(values,reservation);
        if (!Object.keys(changed).length) throw new Error("변경한 항목이 없습니다.");
        await run(() => businessApi.updateReservation(organizationId,reservation.id,{...changed,expected_version:reservation.version,change_reason}));
      } else await run(() => businessApi.createReservation(organizationId,propertyId,{...values,channel:String(form.get("channel")),external_reservation_id:String(form.get("external_reservation_id") ?? "").trim() || null}));
    } catch (e) {setError(e instanceof Error ? e.message : "입력을 확인해 주세요.");}
  }
  const badge = (field: ReservationField) => protectedFields.includes(field) && <span> · 수동 보정</span>;
  return <div className="page-stack">
    {reservation && <p className="text-sm text-slate-600">출처: {reservation.origin === "MANUAL" ? "수동 등록" : "CSV"} · 채널 {reservation.channel} · 예약번호 {reservation.external_reservation_id ?? "없음"} · 버전 {reservation.version}</p>}
    <div className="editor-columns">
      <form onSubmit={submit} aria-label="예약 입력" aria-describedby={error ? "reservation-error" : undefined} className="surface">
        <fieldset disabled={busy || conflict} className="grid gap-7">
          {!reservation && <FieldGroup title="예약 정보">
            <FormField label="채널 (필수)" help="출처 구분이며 OTA 연결이 아닙니다."><select name="channel" className="field">{channels.map(c => <option key={c}>{c}</option>)}</select></FormField>
            <FormField label="외부 예약번호 (선택)" help="직접 등록 시 생략 가능 · 최대 200자"><input name="external_reservation_id" maxLength={200} className="field" /></FormField>
          </FieldGroup>}
          <FieldGroup title="숙박 일정">
            <FormField label={<>체크인 (필수){badge("check_in")}</>}><input type="date" min="1901-01-01" max="9998-12-31" name="check_in" defaultValue={reservation?.check_in} required className="field" /></FormField>
            <FormField label={<>체크아웃 (필수){badge("check_out")}</>} help="체크인 다음 날 이후"><input type="date" min="1901-01-01" max="9998-12-31" name="check_out" defaultValue={reservation?.check_out} required className="field" /></FormField>
          </FieldGroup>
          <FieldGroup title="금액">
            <FormField label={<>총 매출 (원·필수){badge("gross_revenue")}</>} help="0 이상의 원 단위 정수"><input name="gross_revenue" inputMode="numeric" maxLength={18} defaultValue={reservation?.gross_revenue} required className="field" /></FormField>
            <FormField label={<>수수료 (원·선택){badge("channel_fee")}</>} help="총 매출 이하 · 미입력은 0원과 다릅니다."><input name="channel_fee" inputMode="numeric" maxLength={18} defaultValue={reservation?.channel_fee ?? ""} className="field" /></FormField>
          </FieldGroup>
          <FieldGroup title="객실 / 인원">
            <FormField label={<>객실 수 (선택){badge("room_units")}</>} help="입력 시 1 이상의 정수"><input name="room_units" type="number" min="1" max="2147483647" defaultValue={reservation?.room_units ?? ""} className="field" /></FormField>
            <FormField label={<>투숙인원 (선택){badge("guest_count")}</>} help="객실 수와 구분됩니다."><input name="guest_count" type="number" min="1" max="2147483647" defaultValue={reservation?.guest_count ?? ""} className="field" /></FormField>
          </FieldGroup>
          <FormField label={<>상태{badge("reservation_status")}</>}><select name="reservation_status" defaultValue={reservation?.reservation_status ?? "UNKNOWN"} className="field"><option value="UNKNOWN">미확인</option><option value="CONFIRMED">확정</option><option value="CANCELLED">취소</option></select></FormField>
          {reservation && <FormField label="변경 사유 (필수)" help="최대 500자 · 수정 이유를 기록하면 이후 변경 이력에서 확인할 수 있습니다. 취소·재개도 상태를 선택하고 사유를 입력해 저장하세요."><textarea name="change_reason" required maxLength={500} className="field" /></FormField>}
          <div className="form-actions"><Button>{busy ? "저장 중…" : reservation ? "수정 저장" : "예약 직접 등록"}</Button><Link className={buttonClass("secondary")} href={`/properties/${propertyId}/reservations`}>예약 목록</Link></div>
        </fieldset>
        <p id="reservation-error" role="alert" className="validation-error mt-3">{error}</p>
      </form>
      <aside className="grid gap-5" aria-label="예약 입력 안내">
        <DataQualityNotice title={reservation?.origin === "CSV_IMPORT" ? "수동 보정 항목은 보호됩니다." : "직접 등록한 예약입니다."}>
          <p>{reservation?.origin === "CSV_IMPORT" ? "수동으로 수정한 항목은 이후 CSV 가져오기에서 자동으로 덮어쓰지 않습니다." : "고객 이름·연락처를 입력하지 않습니다. 직접 등록에는 외부 예약번호를 생략할 수 있습니다."}</p>
        </DataQualityNotice>
        {protectedFields.length > 0 && <Surface className="grid gap-3"><SectionHeader>CSV 자동 갱신 보호</SectionHeader>{protectedFields.map(f => <Button variant="secondary" disabled={busy || conflict} key={f} onClick={() => setReleaseField(f as ReservationField)}>{reservationFields[f as ReservationField]} · CSV 자동 갱신 허용</Button>)}</Surface>}
        {releaseField && reservation && <form className="surface grid gap-4" aria-label="보호 해제 확인" onSubmit={e => {e.preventDefault();const form = new FormData(e.currentTarget);const change_reason=String(form.get("reason") ?? "").trim();if(!change_reason){setError("변경 사유를 입력해 주세요.");return;}void run(() => businessApi.releaseReservation(organizationId,reservation.id,{fields:[releaseField],expected_version:reservation.version,change_reason})).then(() => setReleaseField(null));}}>
          <p className="text-sm">보호를 해제해도 현재 값은 즉시 바뀌지 않습니다. 다음 CSV 가져오기부터 해당 항목이 다시 갱신될 수 있습니다.</p>
          <FormField label="보호 해제 사유"><textarea name="reason" required maxLength={500} className="field" /></FormField><Button disabled={busy || conflict}>보호 해제 확인</Button><Button variant="secondary" type="button" onClick={() => setReleaseField(null)}>해제 취소</Button>
        </form>}
        {reservation && <Surface className="grid gap-3"><SectionHeader>변경 이력</SectionHeader><p className="text-sm text-slate-600">항목별 변경 전후 값·사유·행위자를 확인하세요.</p><a href="#reservation-history" className={buttonClass("secondary")}>변경 이력 보기</a></Surface>}
        <p className="meta-text">숙박일수와 순매출은 저장된 예약 자료로 계산됩니다. 수수료 미입력은 미확인 상태입니다.</p>
      </aside>
    </div>
    {conflict && <div role="alert"><DataQualityNotice title="최신 예약 정보를 확인해 주세요." severity="warning"><p>다른 변경이 먼저 저장되었거나 예약번호가 중복되었습니다. 최신 예약 정보를 다시 불러온 후 확인해 주세요.</p><Button variant="secondary" className="mt-3" onClick={() => window.location.reload()}>최신 예약 다시 불러오기</Button></DataQualityNotice></div>}
    {reservation && <ReservationHistory items={history} total={historyTotal} offset={historyOffset} />}
  </div>;
}
