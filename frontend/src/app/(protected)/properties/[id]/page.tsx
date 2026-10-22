import Link from "next/link";
import { notFound } from "next/navigation";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { ApiError } from "@/lib/api/transport";
import { PropertyNav } from "@/components/property-nav";
import { DataQualityNotice, PageHeader, SectionHeader, Surface, buttonClass } from "@/components/ui";

export default async function PropertyDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const organization = await requireOrganization();
  const { id } = await params;
  const property = await serverApi.property(organization.organization_id, id).catch((error: unknown) => {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    throw error;
  });
  return <section className="page-stack"><PageHeader title={property.name} eyebrow="숙소 정보" action={<Link href={`/properties/${id}/edit`} className={buttonClass()}>숙소 정보 수정</Link>} />
    <PropertyNav id={id} active="숙소 정보" />
    <div className="detail-columns"><Surface className="grid gap-5"><SectionHeader>기본 정보</SectionHeader><dl className="detail-facts">
      <div><dt>지역 시장 기준</dt><dd>{property.region ? property.region.sido_name + " " + property.region.sigungu_name : "미설정"}</dd></div>
      <div><dt>주소</dt><dd>{property.address}</dd></div>
      <div><dt>도로명 주소</dt><dd>{property.road_address || "미입력"}</dd></div>
      <div><dt>숙소 유형</dt><dd>{property.accommodation_type}</dd></div>
      <div><dt>기본 객실 수 (이력 없는 날짜의 추정값)</dt><dd>{property.inventory_units}</dd></div>
      <div><dt>시간대</dt><dd>{property.timezone}</dd></div>
      <div><dt>위도 / 경도</dt><dd>{property.latitude ?? "미입력"} / {property.longitude ?? "미입력"}</dd></div>
    </dl></Surface><Surface className="grid gap-4"><SectionHeader>숙소 운영</SectionHeader><Link className={buttonClass("secondary")} href={`/properties/${id}/dashboard`}>대시보드</Link><Link className={buttonClass("secondary")} href={`/properties/${id}/reservations`}>예약 목록</Link><Link className={buttonClass("secondary")} href={`/properties/${id}/expenses`}>비용 관리</Link><Link className={buttonClass("secondary")} href={`/properties/${id}/inventory`}>객실 운영 · 이력 / 판매 제외</Link><Link className={buttonClass("secondary")} href={`/properties/${id}/market`}>지역 시장</Link></Surface></div>
    <DataQualityNotice title="기본 객실 수는 날짜별 이력의 대체값입니다."><p>객실 수 이력이 없는 날에만 기본값을 사용합니다. 지역 시장 기준은 선택한 비교 범위이며 주소·위치를 검증한 결과가 아닙니다.</p></DataQualityNotice>
  </section>;
}
