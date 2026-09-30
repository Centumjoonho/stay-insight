"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { businessApi } from "@/lib/api/client";
import type { AccommodationType, PropertyResponse } from "@/lib/api/types";
import type { MarketRegion } from "@/lib/api/region-types";

export const typeLabels: Record<AccommodationType, string> = {
  HOTEL: "호텔", MOTEL: "모텔", HOSTEL: "호스텔", GUESTHOUSE: "게스트하우스",
  LIFESTYLE_ACCOMMODATION: "생활숙박시설", PENSION: "펜션", VACATION_RENTAL: "독채·단기 임대", OTHER: "기타",
};

export function PropertyForm({ organizationId, property }: { organizationId: string; property?: PropertyResponse }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [regions, setRegions] = useState<MarketRegion[]>([]);
  const [regionId, setRegionId] = useState(property?.region_id ?? "");
  const [regionState, setRegionState] = useState<"loading" | "ready" | "error">("loading");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    businessApi.regions().then((items) => {
      if (active) { setRegions(items); setRegionState("ready"); }
    }).catch(() => { if (active) setRegionState("error"); });
    return () => { active = false; };
  }, [attempt]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setError("");
    // A failed lookup must not clear an existing association or submit stale options.
    if (regionState !== "ready") { setError("부산 지역 정보를 불러온 후 저장해 주세요."); return; }
    if (regionId && !regions.some((region) => region.id === regionId)) {
      setError("선택 가능한 부산 구·군을 선택해 주세요."); return;
    }
    setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      const body = {
        name: String(form.get("name")), address: String(form.get("address")),
        road_address: String(form.get("road_address")) || null,
        accommodation_type: String(form.get("type")) as AccommodationType,
        inventory_units: Number(form.get("inventory_units")), region_id: regionId || null,
      };
      const saved = property
        ? await businessApi.updateProperty(organizationId, property.id, body)
        : await businessApi.createProperty(organizationId, body);
      router.replace("/properties/" + saved.id);
      router.refresh();
    } catch (error) {
      setError(error instanceof Error ? error.message : "숙소를 저장할 수 없습니다.");
      setBusy(false);
    }
  }
  return <form onSubmit={submit} className="mt-6 grid max-w-lg gap-4">
    <label>숙소명<input name="name" required maxLength={200} defaultValue={property?.name} className="field" /></label>
    <label>주소<input name="address" required maxLength={500} defaultValue={property?.address} className="field" /></label>
    <label>도로명 주소<input name="road_address" maxLength={500} defaultValue={property?.road_address ?? ""} className="field" /></label>
    <label>숙소 유형<select name="type" defaultValue={property?.accommodation_type ?? "HOTEL"} className="field">{Object.entries(typeLabels).map(([value,label]) =>
      <option key={value} value={value}>{label}</option>)}</select></label>
    <label>객실 수<input name="inventory_units" type="number" min={1} max={2147483647} step={1} defaultValue={property?.inventory_units ?? 1} required className="field" /></label>
    <label>부산 구·군<select name="region_id" className="field" value={regionId}
      disabled={busy || regionState !== "ready"} aria-describedby="region-help region-status"
      onChange={(event) => setRegionId(event.target.value)}>
      <option value="">지역 미설정</option>
      {regionId && !regions.some((r) => r.id === regionId) && <option value={regionId}>
        {property?.region?.sigungu_name ?? "기존 선택 지역 (확인 필요)"}
      </option>}
      {regions.map((region) => <option key={region.id} value={region.id}>{region.sigungu_name}</option>)}
    </select></label>
    <p id="region-help" className="text-sm text-slate-600">선택한 구·군을 기준으로 공식 숙박업 시장정보를 제공합니다. 실제 주소와 별도로 설정하며 주소 변경 시 자동 변경되지 않습니다.</p>
    <div id="region-status" role="status">
      {regionState === "loading" && "부산 지역 정보를 불러오는 중…"}
      {regionState === "ready" && !regions.length && "선택 가능한 부산 지역 정보가 없습니다."}
      {regionState === "error" && <>부산 지역 정보를 불러올 수 없습니다. <button type="button" className="underline"
        onClick={() => { setRegionState("loading"); setAttempt((value) => value + 1); }}>다시 시도</button></>}
    </div>
    <button disabled={busy || regionState !== "ready"} className="action">{busy ? "저장 중…" : property ? "숙소 수정 저장" : "숙소 등록"}</button>
    <p role="alert">{error}</p>
  </form>;
}
