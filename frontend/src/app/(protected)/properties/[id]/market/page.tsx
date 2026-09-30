import { VisitorView } from "@/components/visitor-view";
import { notFound } from "next/navigation";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { ApiError } from "@/lib/api/transport";
import { MarketView } from "@/components/market-view";

export default async function Market({ params, searchParams }: { params: Promise<{ id: string }>; searchParams?: Promise<{ category?: string }> }) {
  const { id } = await params;
  const org = await requireOrganization();
  let data;
  try {
    data = await serverApi.accommodationMarket(org.organization_id, id);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    // Existing protected error boundary handles authorization and API failures.
    throw error;
  }
  const query = await searchParams;
  const category = query?.category && ["1", "2", "3"].includes(query.category) ? query.category : "2";
  let visitors = null;
  try {
    visitors = await serverApi.visitorMarket(org.organization_id, id, category);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status < 500) throw error;
  }
  return <><MarketView data={data} /><VisitorView data={visitors} error={!visitors} /></>;
}
