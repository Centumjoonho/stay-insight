import Link from "next/link";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { PageHeader, SectionHeader, StatusBadge, Surface, buttonClass } from "@/components/ui";

export default async function PropertiesPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const organization = await requireOrganization();
  const params = await searchParams;
  const page = Math.max(1, Math.min(1000000, Number.parseInt(params.page ?? "1", 10) || 1));
  const properties = await serverApi.properties(organization.organization_id, (page - 1) * 50);
  return <section className="page-stack properties-page">
    <PageHeader title="내 숙소" eyebrow={organization.organization_name} action={<Link href="/properties/new" className={buttonClass()}>＋ 숙소 등록</Link>} />
    <SectionHeader description="숙소를 선택해 상세 정보를 확인하세요.">등록한 숙소</SectionHeader>
    {!properties.total && <Surface className="grid justify-items-center gap-4 py-10"><h2 className="text-lg font-semibold">등록한 숙소가 없습니다.</h2><p className="text-sm">숙소를 등록하면 이곳에서 확인할 수 있습니다.</p><Link href="/properties/new" className={buttonClass()}>숙소 등록</Link></Surface>}
    <ul className="grid gap-4">{properties.items.map((property) => <li key={property.id} className="surface property-card">
      <div className="property-identity"><span aria-hidden="true" className="property-symbol">▤</span><div className="min-w-0 flex-1"><Link href={`/properties/${property.id}`} className="property-name">{property.name}</Link><p className="property-address">{property.address}</p></div>{property.name.includes("[개발용 더미]") && <StatusBadge tone="info">개발용 더미</StatusBadge>}</div>
      <div className="property-card-footer"><span className="text-slate-600">기본 객실 수</span><strong>{property.inventory_units}실</strong><Link href={`/properties/${property.id}`} className={buttonClass("quiet")} aria-label={`${property.name} 숙소 상세`}>숙소 상세 <span aria-hidden="true">→</span></Link></div>
    </li>)}</ul>
    <nav aria-label="페이지" className="form-actions justify-end">
      {page > 1 && <Link className={buttonClass("secondary")} href={`/properties?page=${page-1}`}>이전</Link>}
      {page * 50 < properties.total && <Link className={buttonClass("secondary")} href={`/properties?page=${page+1}`}>다음</Link>}
    </nav>
  </section>;
}
