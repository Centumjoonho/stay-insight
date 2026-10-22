import { requireOrganization, serverApi } from "@/lib/api/server";
import { ReservationEditor } from "@/components/reservation-editor";
import { PageHeader } from "@/components/ui";
import { PropertyNav } from "@/components/property-nav";
export default async function NewReservation({params}: {params: Promise<{id:string}>}) {
  const {id}=await params; const org=await requireOrganization();
  const property=await serverApi.property(org.organization_id,id);
  return <section className="page-stack"><PageHeader title="예약 직접 등록" eyebrow={property.name} /><PropertyNav id={id} active="예약 목록" /><ReservationEditor organizationId={org.organization_id} propertyId={id} /></section>;
}
