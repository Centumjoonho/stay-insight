import Link from "next/link";
import { requireOrganization, serverApi } from "@/lib/api/server";

export default async function PropertiesPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const organization = await requireOrganization();
  const params = await searchParams;
  const page = Math.max(1, Math.min(1000000, Number.parseInt(params.page ?? "1", 10) || 1));
  const properties = await serverApi.properties(organization.organization_id, (page - 1) * 50);
  return <section>
    <h1 className="text-2xl font-semibold">내 숙소</h1>
    <p className="mt-2">{organization.organization_name}</p>
    <Link href="/properties/new" className="action mt-6 inline-block">숙소 등록</Link>
    {!properties.total && <p className="mt-8">등록한 숙소가 없습니다.</p>}
    <ul className="mt-6 grid gap-3">{properties.items.map((property) => <li key={property.id} className="rounded border bg-white p-4">
      <Link href={`/properties/${property.id}`} className="font-semibold underline">{property.name}</Link>
      <p>{property.address}</p><p>객실 수: {property.inventory_units}</p>
    </li>)}</ul>
    <nav aria-label="페이지" className="mt-6 flex gap-4">
      {page > 1 && <Link href={`/properties?page=${page-1}`}>이전</Link>}
      {page * 50 < properties.total && <Link href={`/properties?page=${page+1}`}>다음</Link>}
    </nav>
  </section>;
}
