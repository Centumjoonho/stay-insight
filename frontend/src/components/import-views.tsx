import type { ColumnMapping, CsvPreview, ImportResult, ValidationResult } from "@/lib/api/import-types";
import { mappingFields } from "@/lib/imports";

export function CsvPreviewTable({ preview }: { preview: CsvPreview }) {
  return <section aria-label="데이터 미리보기">
    <h2>2. 데이터 미리보기</h2>
    <p>인코딩: {preview.encoding} · 총 {preview.total_rows}행 · 처음 10행 표시</p>
    <div className="overflow-auto"><table className="w-full border-collapse text-left">
      <thead><tr>{preview.headers.map((header) => <th className="border p-2" key={header}>{header}</th>)}</tr></thead>
      <tbody>{preview.rows.map((row, index) => <tr key={index}>{row.map((cell, col) =>
        <td className="max-w-64 break-words border p-2" key={col}>{cell}</td>)}</tr>)}</tbody>
    </table></div>
    {preview.warnings.map((warning) => <p key={warning}>{warning}</p>)}
  </section>;
}

export function MappingFields({ headers, mapping, onChange, disabled }: {
  headers: string[]; mapping: ColumnMapping; onChange: (field: string, value: string) => void; disabled: boolean;
}) {
  return <fieldset disabled={disabled} className="grid gap-3"><legend>3. 열 연결</legend>
    {mappingFields.map(([field, label, required]) => <label key={field}>
      {label}{required ? " (필수)" : " (선택)"}
      <select className="field" value={mapping[field] ?? ""} required={required}
        onChange={(event) => onChange(field, event.target.value)}>
        <option value="">CSV 열 선택</option>
        {headers.map((header) => <option value={header} key={header}>{header}</option>)}
      </select></label>)}
  </fieldset>;
}

export function ValidationSummary({ result }: { result: ValidationResult }) {
  return <section aria-label="검증 결과"><h2>4. 검증 결과</h2>
    <p>총 {result.total_rows}건 · 정상 {result.valid_rows}건 · 오류 {result.invalid_rows}건</p>
    {result.invalid_rows > 0 && <p>오류를 수정한 파일을 다시 선택해 주세요. 일부 행만 가져오지 않습니다.</p>}
    <ul>{result.errors.map((error, index) =>
      <li key={index}>{error.row}행 / {error.field}: {error.message}</li>)}</ul>
    {result.errors_truncated && <p>처음 100개 오류만 표시합니다.</p>}
    <ul>{result.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
  </section>;
}

export function ImportResultView({ result }: { result: ImportResult }) {
  return <section aria-label="가져오기 결과"><h2>6. 가져오기 결과</h2>
    <p>{result.status === "COMPLETED" ? "가져오기 완료" : "가져오기 실패"}</p>
    {result.duplicate && <p>이미 가져온 파일입니다. 기존 결과를 표시합니다.</p>}
    <dl><div><dt>총 행</dt><dd>{result.total_rows}건</dd></div>
      <div><dt>처리 완료</dt><dd>{result.imported_rows}건</dd></div>
      <div><dt>신규 / 갱신</dt><dd>{result.inserted_rows} / {result.updated_rows}건</dd></div>
      <div><dt>검증 오류</dt><dd>{result.rejected_rows}건</dd></div></dl>
    {result.error_message && <p role="alert">{result.error_message}</p>}
    {result.status === "FAILED" && <p>예약 변경은 저장되지 않았습니다.</p>}
    <ul>{result.validation_errors.map((error, index) =>
      <li key={index}>{error.row}행 / {error.field}: {error.message}</li>)}</ul>
  </section>;
}
