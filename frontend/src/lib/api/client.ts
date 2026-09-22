import type { Channel, ColumnMapping, CsvPreview, ImportResult, ValidationResult } from "./import-types";
import { importForm } from "@/lib/imports";
import { browserAuth } from "@/lib/supabase/client";
import { apiRequest, ApiError } from "./transport";
import type { MeResponse, OrganizationResponse, PropertyCreate, PropertyResponse } from "./types";

async function request<T>(path: string, options?: RequestInit, organizationId?: string): Promise<T> {
  const { data, error } = await browserAuth().auth.getSession();
  try {
    return await apiRequest<T>(
      process.env.NEXT_PUBLIC_API_BASE_URL,
      error ? undefined : data.session?.access_token,
      path, options, organizationId,
    );
  } catch (error) {
    // A rejected session must also discard the browser router cache.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    if (error instanceof ApiError && error.status === 401) window.location.assign("/login");
    throw error;
  }
}

export const businessApi = {
  previewCsv: (file: File) => {
    const body = new FormData(); body.set("file", file);
    return request<CsvPreview>("/api/v1/imports/preview", { method: "POST", body });
  },
  validateImport: (org: string, property: string, channel: Channel, mapping: ColumnMapping, file: File) =>
    request<ValidationResult>("/api/v1/imports/validate", {
      method: "POST", body: importForm(file, property, channel, mapping),
    }, org),
  importCsv: (org: string, property: string, channel: Channel, mapping: ColumnMapping, file: File) =>
    request<ImportResult>("/api/v1/imports", {
      method: "POST", body: importForm(file, property, channel, mapping),
    }, org),
  me: () => request<MeResponse>("/api/v1/me"),
  onboard: (organization_name: string) =>
    request<OrganizationResponse>("/api/v1/onboarding", {
      method: "POST", body: JSON.stringify({ organization_name }),
    }),
  createProperty: (organizationId: string, body: PropertyCreate) =>
    request<PropertyResponse>("/api/v1/properties", {
      method: "POST", body: JSON.stringify(body),
    }, organizationId),
};
