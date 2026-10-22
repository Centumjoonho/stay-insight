import Link from "next/link";
import type { DashboardSummary, DashboardTrends } from "@/lib/api/dashboard-types";
import { expenseCategories } from "@/lib/api/expense-types";
import { comparisonText, currency, decimalText, percentage, periodCaption } from "@/lib/dashboard";
import { DashboardCharts } from "./dashboard-charts";
import { PropertyNav } from "@/components/property-nav";
import { DataQualityNotice, KpiCard, PageHeader, SectionHeader } from "@/components/ui";

export function DashboardView({ summary: s, trends }: { summary: DashboardSummary; trends: DashboardTrends }) {
  const f = s.financial, o = s.operations, q = s.data_quality;
  const root = `/properties/${s.property.id}`;
  const hasReservations = q.has_financial_reservations || q.has_operational_reservations;
  const cards: { key: string; label: string; value: string; kind: "money" | "count" | "ratio"; estimated?: boolean }[] = [
    { key: "recognized_gross_revenue", label: "매출", value: currency(f.recognized_gross_revenue), kind: "money" },
    { key: "known_operating_profit", label: "확인된 영업이익", value: currency(f.known_operating_profit), kind: "money" },
    { key: "occupancy_rate", label: "점유율", value: percentage(o.occupancy_rate), kind: "ratio", estimated: true },
    { key: "adr", label: "ADR", value: currency(o.adr), kind: "money", estimated: true },
    { key: "revpar", label: "RevPAR", value: currency(o.revpar), kind: "money", estimated: true },
    { key: "known_cost_total", label: "운영비", value: currency(f.known_cost_total), kind: "money" },
    { key: "reservation_count", label: "예약건수", value: decimalText(o.reservation_count) + "건", kind: "count" },
    { key: "average_length_of_stay", label: "평균 숙박일수", value: o.average_length_of_stay === null ? "계산 불가" : decimalText(o.average_length_of_stay, 1) + "박", kind: "ratio" },
  ];
  const card = (c: typeof cards[number], primary = false) => <KpiCard key={c.key} label={c.label} value={c.value} estimated={c.estimated} primary={primary}
    comparison={<>전월 {s.period.is_partial ? "동기간 " : ""}대비 {comparisonText(s.comparisons.previous_month.metrics[c.key], c.kind)}</>}
    yearComparison={<>전년 동월 {s.period.is_partial ? "동기간 " : ""}대비 {comparisonText(s.comparisons.previous_year.metrics[c.key], c.kind)}</>} />;
  return <section className="page-stack">
    <PageHeader title="대시보드" eyebrow={s.property.name} description={periodCaption(s.period)} action={
      <form className="flex items-end gap-2" aria-label="대시보드 월 선택">
        <label>조회 월<input className="field" name="month" type="month" min="1901-01"
          defaultValue={s.period.month} required /></label><button className="action">조회</button>
      </form>} />
    <PropertyNav id={s.property.id} active="대시보드" />
    {!hasReservations ? <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8">
      <h2 className="text-xl font-semibold">아직 분석할 예약 데이터가 없습니다.</h2>
      <p className="my-3 text-slate-600">선택한 기간의 분석 대상 예약이 없습니다. 실제 영업활동이 없었다는 뜻은 아닙니다.</p>
      <Link className="underline" href={root + "/imports/new"}>CSV 가져오기</Link>
    </div> : <div aria-label="주요 운영 지표" className="page-stack">
      <SectionHeader>재무 요약</SectionHeader><div className="kpi-primary-grid">{cards.slice(0, 2).map(c => card(c, true))}</div>
      <p className="text-sm text-slate-600">등록된 매출과 입력된 운영비 기준이며, 세금·이자·감가상각 등 미등록 비용은 포함되지 않을 수 있습니다.</p>
      {!!q.warnings.length && <DataQualityNotice title="데이터 확인 필요" severity={q.warnings.some(w => /OVER|ZERO/.test(w.code)) ? "warning" : "info"}>
        <ul>{q.warnings.map(w => <li key={w.code}>{w.message}</li>)}</ul><p className="mt-2">체크인 기준 UNKNOWN {q.unknown_status_count}건 · 수수료 입력 {q.channel_fee_known_count}건 / 미입력 {q.channel_fee_missing_count}건</p>
      </DataQualityNotice>}
      <SectionHeader>객실 운영 · 예약 자료 기반 추정</SectionHeader><div className="kpi-operating-grid">{cards.slice(2, 5).map(c => card(c))}</div>
      <div className="kpi-support-grid">{cards.slice(5).map(c => card(c))}</div>
    </div>}
    {!hasReservations && !!q.warnings.length && <DataQualityNotice title="데이터 확인 필요"><ul>{q.warnings.map(w => <li key={w.code}>{w.message}</li>)}</ul><p>체크인 기준 UNKNOWN {q.unknown_status_count}건 · 수수료 입력 {q.channel_fee_known_count}건 / 미입력 {q.channel_fee_missing_count}건</p></DataQualityNotice>}
    <details className="surface"><summary className="cursor-pointer py-2 font-semibold">지표 집계 기준과 비교 기간</summary><div className="mt-3 space-y-2 text-sm text-slate-600">
      {hasReservations && <p>확인된 영업이익률: {percentage(f.known_operating_margin)} · 전월 대비 {comparisonText(s.comparisons.previous_month.metrics.known_operating_margin, "ratio")}</p>}
      <p>등록된 매출과 입력된 운영비를 기준으로 계산한 값이며, 세금·이자·감가상각 등 미등록 비용은 포함되지 않을 수 있습니다.</p>
      <p>매출·수수료는 체크인일 기준이며 취소 예약을 제외합니다. UNKNOWN 예약은 포함됩니다.</p>
      {s.metadata.calculation_version === "dashboard-v2" ? <p>날짜별 객실 수 이력에서 판매 제외 객실을 차감합니다. 예약별 객실 수를 반영하며, 미입력 예약은 1객실로 추정합니다. 실투숙 확인 자료는 아닙니다.</p> : <>
        <p>등록 객실 수와 달력 일수를 기준으로 계산한 점유율입니다. 판매중지·객실차단 일정은 아직 반영되지 않습니다.</p>
        <p>예약 1건을 객실 1개로 가정한 추정치입니다. 실투숙 확인 자료는 없으며 현재 등록 객실 수를 과거 기간에도 적용합니다.</p>
      </>}
      <p>ADR·RevPAR는 예약 매출을 숙박일수에 비례 배분한 추정치입니다. 체크아웃일은 제외합니다.</p>
      {hasReservations && <p>기간 내 예약 객실박 (추정): {o.occupied_room_nights}박 / 가용 객실박: {o.available_room_nights}박</p>}
      <p>전월 비교: {s.comparisons.previous_month.period.start_date} ~ {s.comparisons.previous_month.period.end_date} · 전년 비교: {s.comparisons.previous_year.period.start_date} ~ {s.comparisons.previous_year.period.end_date}</p>
    </div></details>
    <DashboardCharts items={trends.items} />
    <p className="text-xs text-slate-500">자료 없는 달은 선을 연결하지 않습니다. 현재 월은 오늘까지이며 과거 월은 전체 월입니다. 큰 금액의 차트 좌표는 근사값이며 안전한 숫자 범위를 넘으면 생략합니다.</p>
    <details className="rounded border border-slate-200 bg-white p-4"><summary>월별 수치 표 보기</summary>
      <div className="overflow-x-auto"><table className="mt-3 w-full text-left text-sm"><caption className="sr-only">월별 추이 원본 수치</caption>
        <thead><tr>{["월", "매출", "확인된 총 비용", "확인된 영업이익", "점유율 (추정)"].map((label) => <th className="p-2" scope="col" key={label}>{label}</th>)}</tr></thead>
        <tbody>{trends.items.map((row) => <tr key={row.month} className="border-t">
          <th scope="row" className="p-2">{row.month}{row.is_partial ? " (오늘까지)" : ""}</th>
          <td>{row.has_financial_reservations ? currency(row.recognized_gross_revenue) : "자료 없음"}</td>
          <td>{row.has_financial_reservations || row.expense_count > 0 ? currency(row.known_cost_total) : "자료 없음"}</td>
          <td>{row.has_financial_reservations ? currency(row.known_operating_profit) : "계산 불가"}</td>
          <td>{row.has_operational_reservations ? percentage(row.occupancy_rate) : "자료 없음"}</td>
        </tr>)}</tbody></table></div>
    </details>
    <div className="analysis-grid">
      <section className="surface">
        <h2 className="mb-4 text-lg font-semibold">예약 채널별 매출</h2>
        <div className="table-scroll channel-table"><table className="data-table">
          <caption className="sr-only">체크인 기준 채널 성과</caption><thead><tr>{["채널", "예약", "매출", "매출 비중", "플랫폼 수수료"].map((label) => <th scope="col" className="p-2" key={label}>{label}</th>)}</tr></thead>
          <tbody>{s.channels.map((c) => <tr key={c.channel} className="border-t">
            <th scope="row" className="p-2">{c.channel}</th><td>{c.reservation_count}건</td>
            <td>{currency(c.recognized_gross_revenue)}</td><td>{percentage(c.revenue_share_percent)}</td>
            <td>{c.known_channel_fee === null ? "-" : currency(c.known_channel_fee)}
              {c.channel_fee_missing_count > 0 && <span className="block text-xs text-slate-600">미입력 {c.channel_fee_missing_count}건</span>}</td>
          </tr>)}</tbody></table></div><div className="channel-mobile">{s.channels.map(c => <div key={c.channel} className="border-b border-slate-200 py-3"><h3 className="font-semibold">{c.channel}</h3><p className="text-sm">예약 {c.reservation_count}건 · 매출 {currency(c.recognized_gross_revenue)} · 비중 {percentage(c.revenue_share_percent)}</p><p className="meta-text">플랫폼 수수료 {c.known_channel_fee === null ? "-" : currency(c.known_channel_fee)}{c.channel_fee_missing_count > 0 && ` · 미입력 ${c.channel_fee_missing_count}건`}</p></div>)}</div>{!s.channels.length && <p className="mt-3 text-sm text-slate-600">기간 내 체크인 예약이 없습니다.</p>}
      </section>
      <section className="surface">
        <h2 className="mb-4 text-lg font-semibold">확인된 비용 구성</h2>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between gap-3"><dt>직접 입력 운영비</dt><dd>{currency(f.manual_expense_total)}</dd></div>
          <div className="flex justify-between gap-3"><dt>고정비 / 변동비</dt><dd>{currency(f.fixed_expense_total)} / {currency(f.variable_expense_total)}</dd></div>
          <div className="flex justify-between gap-3"><dt>플랫폼 수수료 · 예약 자료</dt><dd>{q.channel_fee_known_count ? currency(f.known_channel_fee_total) : "-"}</dd></div>
          <div className="flex justify-between gap-3 border-t pt-2 font-semibold"><dt>확인된 총 비용</dt><dd>{currency(f.known_cost_total)}</dd></div>
        </dl>
        {!q.expense_count && <p className="mt-4 text-sm">등록된 운영비가 없습니다. <Link className="underline" href={root + "/expenses"}>비용 관리</Link></p>}
        <ul className="mt-4 space-y-1 text-sm text-slate-600">{s.category_breakdown.map((row) =>
          <li key={row.category}>{expenseCategories[row.category as keyof typeof expenseCategories] ?? row.category}: {currency(row.amount)}</li>)}</ul>
      </section>
    </div>
    <footer className="text-xs text-slate-500">출처: 소유자 예약 (CSV·직접 입력·수동 보정) / 직접 입력 운영비{s.metadata.calculation_version === "dashboard-v2" && " / 객실 운영 입력"} · 등록 자료 기준 · {s.metadata.calculation_version}</footer>
  </section>;
}
