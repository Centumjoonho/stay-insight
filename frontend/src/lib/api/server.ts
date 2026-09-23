import type { DashboardSummary, DashboardTrends } from "./dashboard-types";
import type { Expense, ExpenseSummary } from "./expense-types";
import type { ImportResult, Page, Reservation } from "./import-types";
import { redirect } from "next/navigation";
import { serverAuth } from "@/lib/supabase/server";
import { apiRequest, ApiError } from "./transport";
import type { MeResponse, PropertyListResponse, PropertyResponse } from "./types";

export async function requireToken() {
  const auth = await serverAuth();
  if (!auth) redirect("/login");
  const { data, error } = await auth.auth.getClaims();
  if (error || !data?.claims) redirect("/login");
  // Session is used only to transport the token; getClaims and FastAPI verify it.
  const { data: session } = await auth.auth.getSession();
  if (!session.session) redirect("/login");
  return session.session.access_token;
}

async function request<T>(path: string, organizationId?: string): Promise<T> {
  const token = await requireToken();
  try {
    return await apiRequest<T>(
      process.env.API_INTERNAL_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL,
      token, path, undefined, organizationId,
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/login");
    throw error;
  }
}

export const serverApi = {
  dashboardSummary: (org: string, property: string, month?: string) =>
    request<DashboardSummary>("/api/v1/dashboard/summary?" + new URLSearchParams({ property_id: property, ...(month ? { month } : {}) }), org),
  dashboardTrends: (org: string, property: string, month?: string) =>
    request<DashboardTrends>("/api/v1/dashboard/trends?" + new URLSearchParams({ property_id: property, months: "12", ...(month ? { month } : {}) }), org),
  expenses: (org: string, query: string) => request<Page<Expense>>("/api/v1/expenses?" + query, org),
  expenseSummary: (org: string, query: string) => request<ExpenseSummary>("/api/v1/expenses/summary?" + query, org),
  expense: (org: string, id: string) => request<Expense>("/api/v1/expenses/" + encodeURIComponent(id), org),
  imports: (org: string, query: string) => request<Page<ImportResult>>("/api/v1/imports?" + query, org),
  reservations: (org: string, query: string) => request<Page<Reservation>>("/api/v1/reservations?" + query, org),
  me: () => request<MeResponse>("/api/v1/me"),
  properties: (organizationId: string, offset = 0) =>
    request<PropertyListResponse>(`/api/v1/properties?limit=50&offset=${offset}`, organizationId),
  property: (organizationId: string, id: string) =>
    request<PropertyResponse>(`/api/v1/properties/${encodeURIComponent(id)}`, organizationId),
};

export async function requireOrganization() {
  const me = await serverApi.me();
  if (!me.memberships.length) redirect("/onboarding");
  // Phase 2 UI operates on the first membership; API validates it independently.
  return me.memberships[0];
}
