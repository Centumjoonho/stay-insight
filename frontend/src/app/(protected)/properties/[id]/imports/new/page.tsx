import { requireOrganization, serverApi } from "@/lib/api/server";
import { ImportWizard } from "@/components/import-wizard";

export default async function ImportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const org = await requireOrganization();
  const property = await serverApi.property(org.organization_id, id);
  return <section><h1 className="mb-6 text-2xl font-semibold">{property.name} · CSV 가져오기</h1>
    <ImportWizard propertyId={property.id} organizationId={org.organization_id} /></section>;
}
