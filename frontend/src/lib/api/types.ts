// API transport contracts. No database access or business calculation logic.
export type AccommodationType = "HOTEL" | "MOTEL" | "HOSTEL" | "GUESTHOUSE" |
  "LIFESTYLE_ACCOMMODATION" | "PENSION" | "VACATION_RENTAL" | "OTHER";
export interface MeResponse {
  user_id: string;
  memberships: { organization_id: string; organization_name: string; role: "OWNER" | "MEMBER" }[];
}
export interface OrganizationResponse { id: string; name: string; created_at: string; updated_at: string }
export interface PropertyCreate {
  name: string;
  address: string;
  road_address?: string | null;
  accommodation_type: AccommodationType;
  inventory_units: number;
  latitude?: number | null;
  longitude?: number | null;
  timezone?: "Asia/Seoul";
}
export interface PropertyResponse extends PropertyCreate {
  id: string; organization_id: string; created_at: string; updated_at: string; timezone: "Asia/Seoul";
}
export interface PropertyListResponse { items: PropertyResponse[]; total: number }
