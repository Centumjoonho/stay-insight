import { notFound } from "next/navigation";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { ReservationEditor } from "@/components/reservation-editor";
import { PageHeader } from "@/components/ui";
import { PropertyNav } from "@/components/property-nav";
export default async function ReservationDetail({params,searchParams}: {
  params:Promise<{id:string;reservationId:string}>;searchParams:Promise<{history_offset?:string}>;
}) {
  const {id,reservationId}=await params;const org=await requireOrganization();
  const property=await serverApi.property(org.organization_id,id);
  const reservation=await serverApi.reservation(org.organization_id,reservationId);
  if(reservation.property_id !== id) notFound();
  const offset=Math.max(0,Math.floor(Number((await searchParams).history_offset)||0));
  const history=await serverApi.reservationHistory(org.organization_id,reservationId,offset);
  return <section className="page-stack"><PageHeader title="예약 상세·수정" eyebrow={property.name} /><PropertyNav id={id} active="예약 목록" /><ReservationEditor key={`${reservation.id}:${reservation.version}`} organizationId={org.organization_id} propertyId={id} reservation={reservation} history={history.items} historyTotal={history.total} historyOffset={offset}/></section>;
}
