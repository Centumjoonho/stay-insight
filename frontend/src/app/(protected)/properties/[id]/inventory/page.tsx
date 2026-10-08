import Link from "next/link";
import { notFound } from "next/navigation";
import { InventoryManager } from "@/components/inventory-manager";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { ApiError } from "@/lib/api/transport";

export default async function InventoryPage({ params, searchParams }: {
  params: Promise<{ id: string }>; searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { id } = await params;
  const org = await requireOrganization();
  const search = await searchParams;
  const today = new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Seoul" }).format(new Date());
  const start = search.start ?? today.slice(0, 7) + "-01";
  const end = search.end ?? today;
  if (typeof start !== "string" || typeof end !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(start) || !/^\d{4}-\d{2}-\d{2}$/.test(end))
    return <p role="alert">올바른 날짜 범위를 선택해 주세요. <Link href={`/properties/${id}/inventory`}>다시 조회</Link></p>;
  let property, periods, days;
  try {
    [property, periods, days] = await Promise.all([
      serverApi.property(org.organization_id, id), serverApi.capacity(org.organization_id, id),
      serverApi.availability(org.organization_id, id, start, end),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    if (error instanceof ApiError && error.status === 422) return <p role="alert">조회 범위는 최대 366일입니다. <Link href={`/properties/${id}/inventory`}>다시 조회</Link></p>;
    throw error;
  }
    return <section className="space-y-6"><h1 className="text-2xl font-semibold">{property.name} · 객실 운영</h1>
      <nav className="flex gap-4 underline"><Link href={`/properties/${id}`}>숙소 정보</Link><Link href={`/properties/${id}/dashboard`}>대시보드</Link><Link href={`/properties/${id}/market`}>지역 시장</Link></nav>
      <p>기본 객실 수: {property.inventory_units}실 · 이력이 없는 날짜의 추정과 기존 v1 계산에 사용됩니다.</p>
      <InventoryManager organizationId={org.organization_id} propertyId={id} periods={periods} days={days} today={today} />
    </section>;

}
