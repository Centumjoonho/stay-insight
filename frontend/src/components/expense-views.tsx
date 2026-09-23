import Link from "next/link";
import { costTypes, expenseCategories, type Expense, type ExpenseSummary } from "@/lib/api/expense-types";
import { won } from "@/lib/expenses";
import { ExpenseDelete } from "./expense-delete";

export function ExpenseSummaryView({ summary }: { summary: ExpenseSummary }) {
  return <section aria-label="비용 요약" className="my-6 rounded border bg-white p-4">
    <h2 className="text-xl font-semibold">기간 비용 요약</h2>
    <p>{summary.from_date} ~ {summary.to_date} · 항목·유형 필터와 관계없이 해당 기간 전체 비용입니다.</p>
    <dl className="my-4 grid gap-3 sm:grid-cols-2">
      <div><dt>총 직접입력 운영비</dt><dd>{won(summary.manual_expense_total)}</dd></div>
      <div><dt>고정비</dt><dd>{won(summary.fixed_expense_total)}</dd></div>
      <div><dt>변동비</dt><dd>{won(summary.variable_expense_total)}</dd></div>
      <div><dt>예약 데이터 기반 플랫폼 수수료</dt><dd>{won(summary.channel_fee_total)}</dd></div>
      <div><dt>확인된 총 비용</dt><dd>{won(summary.known_cost_total)}</dd></div>
    </dl>
    <p>플랫폼 수수료: 예약 데이터에서 자동 집계 · 읽기 전용 · 체크인일 기준 (양 끝 포함)</p>
    <p>수수료 입력 예약 {summary.reservations_with_fee}건 / 수수료 미입력 예약 {summary.reservations_missing_fee}건</p>
    <p>미입력 수수료와 기록되지 않은 운영비는 제외됩니다. 전체 비용이나 영업이익을 의미하지 않습니다.</p>
    <h3 className="mt-4 font-semibold">직접 입력 비용 항목별 합계</h3>
    <ul>{summary.category_breakdown.map((row) => <li key={row.category}>{expenseCategories[row.category]}: {won(row.amount)}</li>)}</ul>
  </section>;
}
export function ExpenseTable({ items, organizationId, propertyId }: {
  items: Expense[]; organizationId: string; propertyId: string;
}) {
  return <div className="overflow-x-auto"><table className="w-full text-left">
    <caption className="text-left">직접 입력 비용</caption>
    <thead><tr>{["날짜", "비용 항목", "유형", "금액", "메모", "수정", "삭제"].map((label) =>
      <th scope="col" className="p-2" key={label}>{label}</th>)}</tr></thead>
    <tbody>{items.map((item) => <tr key={item.id} className="border-t">
      <td className="p-2">{item.expense_date}</td><td>{expenseCategories[item.category]}</td>
      <td>{costTypes[item.cost_type]}</td><td>{won(item.amount)}</td><td className="whitespace-pre-wrap">{item.memo}</td>
      <td><Link href={`/properties/${propertyId}/expenses/${item.id}/edit`}>수정</Link></td>
      <td><ExpenseDelete organizationId={organizationId} expenseId={item.id} /></td>
    </tr>)}</tbody></table>{!items.length && <p>선택한 조건에 직접 입력 비용이 없습니다.</p>}</div>;
}
