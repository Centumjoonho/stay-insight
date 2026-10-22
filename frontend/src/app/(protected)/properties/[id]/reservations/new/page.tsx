import Link from "next/link";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { ReservationEditor } from "@/components/reservation-editor";
export default async function NewReservation({params}: {params: Promise<{id:string}>}) {
  const {id}=await params; const org=await requireOrganization();
  const property=await serverApi.property(org.organization_id,id);
  return <section><h1 className="text-2xl font-semibold">{property.name} · 예약 직접 등록</h1><Link href={`/properties/${id}/reservations`}>예약 목록</Link><ReservationEditor organizationId={org.organization_id} propertyId={id} /></section>;
}