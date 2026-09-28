import { notFound } from "next/navigation";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { ApiError } from "@/lib/api/transport";
import { MarketView } from "@/components/market-view";

export default async function Market({ params }: { params: Promise<{ id: string }> }) {
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
  return <MarketView data={data} />;
}
