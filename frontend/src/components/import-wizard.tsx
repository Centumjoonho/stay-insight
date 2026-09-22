"use client";
import { useState } from "react";
import Link from "next/link";
import { businessApi } from "@/lib/api/client";
import { channels, type Channel, type ColumnMapping, type CsvPreview, type ImportResult, type ValidationResult } from "@/lib/api/import-types";
import { mappingErrors } from "@/lib/imports";
import { CsvPreviewTable, ImportResultView, MappingFields, ValidationSummary } from "./import-views";

export function ImportWizard({ propertyId, organizationId }: { propertyId: string; organizationId: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [channel, setChannel] = useState<Channel>("GENERIC");
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [mapping, setMapping] = useState<ColumnMapping>({});
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const errors = preview ? mappingErrors(mapping, preview.headers) : [];
  const invalidate = () => { setValidation(null); setResult(null); setConfirmed(false); setError(""); };
  async function run(action: () => Promise<void>) {
    setBusy(true); setError("");
    try { await action(); } catch (e) { setError(e instanceof Error ? e.message : "요청에 실패했습니다."); }
    finally { setBusy(false); }
  }
  return <div className="grid max-w-5xl gap-6">
    <p>일반 CSV 형식입니다. 채널 선택은 출처 표시이며 Airbnb 등 전용 파일 해석은 제공하지 않습니다.</p>
    <p>최대 5 MiB / 10,000행. 날짜 YYYY-MM-DD, 금액은 KRW 정수입니다. 원본 파일은 보관하지 않습니다.</p>
    <fieldset disabled={busy} className="grid gap-3"><legend>1. CSV 파일 선택</legend>
      <label>채널<select className="field" value={channel} onChange={(e) => {
        setChannel(e.target.value as Channel); invalidate();
      }}>{channels.map((value) => <option key={value}>{value}</option>)}</select></label>
      <label>CSV 파일<input type="file" accept=".csv" onChange={(e) => {
        setFile(e.target.files?.[0] ?? null); setPreview(null); setMapping({}); invalidate();
      }} /></label>
      <button className="action" disabled={!file} onClick={() => run(async () => {
        if (!file) return;
        if (!file.name.toLowerCase().endsWith(".csv") || file.size > 5 * 1024 * 1024)
          throw new Error("5 MiB 이하 CSV 파일을 선택해 주세요.");
        setPreview(await businessApi.previewCsv(file));
      })}>미리보기</button>
    </fieldset>
    {preview && <>
      <CsvPreviewTable preview={preview} />
      <MappingFields headers={preview.headers} mapping={mapping} disabled={busy}
        onChange={(field, value) => { setMapping({ ...mapping, [field]: value }); invalidate(); }} />
      <ul>{errors.map((message, index) => <li key={index}>{message}</li>)}</ul>
      <button className="action" disabled={busy || errors.length > 0} onClick={() => run(async () => {
        if (file) setValidation(await businessApi.validateImport(organizationId, propertyId, channel, mapping, file));
      })}>검증하기</button>
    </>}
    {validation && <>
      <ValidationSummary result={validation} />
      <label><input type="checkbox" checked={confirmed} disabled={busy || validation.invalid_rows > 0}
        onChange={(e) => setConfirmed(e.target.checked)} /> 총 매출과 수수료의 의미를 확인했습니다.
        동일 예약번호의 기존 값이 갱신되는 것에 동의합니다.</label>
      <button className="action" disabled={busy || !confirmed || validation.invalid_rows > 0 || result?.status === "COMPLETED"}
        onClick={() => run(async () => {
          if (file) setResult(await businessApi.importCsv(organizationId, propertyId, channel, mapping, file));
        })}>5. 가져오기</button>
    </>}
    {busy && <p role="status">처리 중… 창을 닫지 마세요.</p>}
    {error && <p role="alert">{error}</p>}
    {result && <ImportResultView result={result} />}
    <nav className="flex gap-4"><Link className="underline" href={`/properties/${propertyId}/imports`}>가져오기 기록</Link>
      <Link className="underline" href={`/properties/${propertyId}/reservations`}>예약 목록</Link></nav>
  </div>;
}
