import { requireOrganization, serverApi } from "@/lib/api/server";
import { ExpenseForm } from "@/components/expense-form";
import { seoulPeriod } from "@/lib/expenses";

export default async function NewExpense({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const org = await requireOrganization();
  const property = await serverApi.property(org.organization_id, id);
  return <section><h1 className="text-2xl font-semibold">{property.name} · 비용 추가</h1>
    <ExpenseForm organizationId={org.organization_id} propertyId={id} today={seoulPeriod().today} /></section>;
}
