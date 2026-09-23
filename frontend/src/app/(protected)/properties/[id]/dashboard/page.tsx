import Link from "next/link";
import { notFound } from "next/navigation";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { ApiError } from "@/lib/api/transport";
import { selectedMonth } from "@/lib/dashboard";
import { DashboardView } from "@/components/dashboard-view";

export default async function Dashboard({ params, searchParams }: {
  params: Promise<{ id: string }>; searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { id } = await params;
  const org = await requireOrganization();
  let month: string | undefined;
  try { month = selectedMonth(await searchParams); }
  catch { return <p role="alert">월을 YYYY-MM 형식으로 선택해 주세요. <Link href={`/properties/${id}/dashboard`}>이번 달</Link></p>; }
  let summary, trends;
  try {
    summary = await serverApi.dashboardSummary(org.organization_id, id, month);
    // Use the API-resolved month, including at the Seoul month boundary.
    trends = await serverApi.dashboardTrends(org.organization_id, id, summary.period.month);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    if (error instanceof ApiError && error.status === 422) return <p role="alert">현재 월까지의 유효한 월을 선택해 주세요. <Link href={`/properties/${id}/dashboard`}>이번 달</Link></p>;
    throw error;
  }
  return <DashboardView summary={summary} trends={trends} />;
}
