"use client";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { businessApi } from "@/lib/api/client";
import type { AccommodationType } from "@/lib/api/types";

export const typeLabels: Record<AccommodationType, string> = {
  HOTEL: "호텔", MOTEL: "모텔", HOSTEL: "호스텔", GUESTHOUSE: "게스트하우스",
  LIFESTYLE_ACCOMMODATION: "생활숙박시설", PENSION: "펜션", VACATION_RENTAL: "독채·단기 임대", OTHER: "기타",
};

export function PropertyForm({ organizationId }: { organizationId: string }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      const property = await businessApi.createProperty(organizationId, {
        name: String(form.get("name")), address: String(form.get("address")),
        road_address: String(form.get("road_address")) || null,
        accommodation_type: String(form.get("type")) as AccommodationType,
        inventory_units: Number(form.get("inventory_units")),
      });
      router.replace(`/properties/${property.id}`);
    } catch (error) {
      setError(error instanceof Error ? error.message : "숙소를 등록할 수 없습니다.");
      setBusy(false);
    }
  }
  return <form onSubmit={submit} className="mt-6 grid max-w-lg gap-4">
    <label>숙소명<input name="name" required maxLength={200} className="field" /></label>
    <label>주소<input name="address" required maxLength={500} className="field" /></label>
    <label>도로명 주소<input name="road_address" maxLength={500} className="field" /></label>
    <label>숙소 유형<select name="type" className="field">{Object.entries(typeLabels).map(([value,label]) =>
      <option key={value} value={value}>{label}</option>)}</select></label>
    <label>객실 수<input name="inventory_units" type="number" min={1} max={2147483647} step={1} defaultValue={1} required className="field" /></label>
    <button disabled={busy} className="action">{busy ? "등록 중…" : "숙소 등록"}</button>
    <p role="alert">{error}</p>
  </form>;
}
