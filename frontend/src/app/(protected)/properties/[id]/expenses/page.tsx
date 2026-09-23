import Link from "next/link";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { expenseCategories, costTypes } from "@/lib/api/expense-types";
import { expenseQuery } from "@/lib/expenses";
import { ExpenseSummaryView, ExpenseTable } from "@/components/expense-views";

export default async function Expenses({ params, searchParams }: {
  params: Promise<{ id: string }>; searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { id } = await params;
  const org = await requireOrganization();
  const property = await serverApi.property(org.organization_id, id);
  let filters;
  try { filters = expenseQuery(id, await searchParams); }
  catch { return <section><h1>비용 관리</h1><p role="alert">기간, 비용 항목, 유형 또는 페이지를 확인해 주세요.</p>
    <Link href={`/properties/${id}/expenses`}>이번 달 비용 보기</Link></section>; }
  const [result, summary] = await Promise.all([
    serverApi.expenses(org.organization_id, filters.list.toString()),
    serverApi.expenseSummary(org.organization_id, filters.period.toString()),
  ]);
  const page = (offset: number) => { const query = new URLSearchParams(filters.list); query.delete("property_id"); query.set("offset", String(offset)); return "?" + query; };
  return <section><h1 className="text-2xl font-semibold">{property.name} · 비용 관리</h1>
    <nav className="my-4 flex gap-4"><Link href={`/properties/${id}`}>숙소</Link>
      <Link href={`/properties/${id}/expenses/new`}>비용 추가</Link>
      <Link href={`/properties/${id}/reservations`}>예약 목록</Link></nav>
    <form className="flex flex-wrap items-end gap-3" aria-label="비용 필터">
      <label>시작일<input className="field" type="date" name="from" defaultValue={filters.from} required /></label>
      <label>종료일<input className="field" type="date" name="to" defaultValue={filters.to} required /></label>
      <label>비용 항목<select className="field" name="category" defaultValue={filters.category}>
        <option value="">전체</option>{Object.entries(expenseCategories).map(([key,label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>비용 유형<select className="field" name="cost_type" defaultValue={filters.cost_type}>
        <option value="">전체</option>{Object.entries(costTypes).map(([key,label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <button className="action">조회</button>
    </form>
    <ExpenseSummaryView summary={summary} /><p>조회된 직접 입력 비용 {result.total}건</p>
    <ExpenseTable items={result.items} organizationId={org.organization_id} propertyId={id} />
    <nav aria-label="비용 페이지" className="mt-4 flex gap-4">
      {filters.offset > 0 && <Link href={page(Math.max(0, filters.offset - 50))}>이전</Link>}
      {filters.offset + 50 < result.total && <Link href={page(filters.offset + 50)}>다음</Link>}
    </nav>
  </section>;
}
