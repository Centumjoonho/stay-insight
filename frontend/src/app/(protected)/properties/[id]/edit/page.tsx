import { notFound } from "next/navigation";
import { PropertyForm } from "@/components/property-form";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { ApiError } from "@/lib/api/transport";

export default async function EditPropertyPage({ params }: { params: Promise<{ id: string }> }) {
  const organization = await requireOrganization();
  const { id } = await params;
  const property = await serverApi.property(organization.organization_id, id).catch((error: unknown) => {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    throw error;
  });
  return <section><h1 className="text-2xl font-semibold">숙소 정보 수정</h1>
    <PropertyForm key={property.id} organizationId={organization.organization_id} property={property} /></section>;
}
