import { notFound } from "next/navigation";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { ExpenseForm } from "@/components/expense-form";
import { ApiError } from "@/lib/api/transport";
import { seoulPeriod } from "@/lib/expenses";

export default async function EditExpense({ params }: { params: Promise<{ id: string; expenseId: string }> }) {
  const { id, expenseId } = await params;
  const org = await requireOrganization();
  const property = await serverApi.property(org.organization_id, id);
  const expense = await serverApi.expense(org.organization_id, expenseId).catch((error: unknown) => {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    throw error;
  });
  if (expense.property_id !== property.id) notFound();
  return <section><h1 className="text-2xl font-semibold">{property.name} · 비용 수정</h1>
    <ExpenseForm organizationId={org.organization_id} propertyId={property.id} today={seoulPeriod().today} expense={expense} /></section>;
}
