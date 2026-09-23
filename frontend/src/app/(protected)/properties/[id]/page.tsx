import Link from "next/link";
import { notFound } from "next/navigation";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { ApiError } from "@/lib/api/transport";

export default async function PropertyDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const organization = await requireOrganization();
  const { id } = await params;
  const property = await serverApi.property(organization.organization_id, id).catch((error: unknown) => {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    throw error;
  });
  return <section><h1 className="text-2xl font-semibold">{property.name}</h1>
    <dl className="mt-6 grid gap-3 rounded border bg-white p-6">
      <div><dt>주소</dt><dd>{property.address}</dd></div>
      <div><dt>도로명 주소</dt><dd>{property.road_address || "미입력"}</dd></div>
      <div><dt>숙소 유형</dt><dd>{property.accommodation_type}</dd></div>
      <div><dt>객실 수</dt><dd>{property.inventory_units}</dd></div>
      <div><dt>시간대</dt><dd>{property.timezone}</dd></div>
      <div><dt>위도 / 경도</dt><dd>{property.latitude ?? "미입력"} / {property.longitude ?? "미입력"}</dd></div>
    </dl>
    <nav className="mt-6 flex gap-4">
      <Link className="underline" href={`/properties/${id}/dashboard`}>대시보드</Link>
      <Link className="underline" href={`/properties/${id}/expenses`}>비용 관리</Link>
      <Link className="underline" href={`/properties/${id}/imports/new`}>CSV 가져오기</Link>
      <Link className="underline" href={`/properties/${id}/imports`}>가져오기 기록</Link>
      <Link className="underline" href={`/properties/${id}/reservations`}>예약 목록</Link>
    </nav>
  </section>;
}
