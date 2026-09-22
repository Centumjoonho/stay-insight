import { requireOrganization } from "@/lib/api/server";
import { PropertyForm } from "@/components/property-form";
export default async function NewPropertyPage() {
  const organization = await requireOrganization();
  return <section><h1 className="text-2xl font-semibold">숙소 등록</h1>
    <PropertyForm organizationId={organization.organization_id} /></section>;
}
