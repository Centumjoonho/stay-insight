import Link from "next/link";

export function PropertyNav({ id, active }: { id: string; active: string }) {
  const root = `/properties/${id}`;
  const entries = [["숙소 정보", ""], ["대시보드", "/dashboard"], ["예약 목록", "/reservations"], ["비용 관리", "/expenses"], ["객실 운영", "/inventory"], ["지역 시장", "/market"], ["CSV 가져오기", "/imports/new"], ["가져오기 기록", "/imports"]];
  return <nav aria-label="숙소 업무" className="property-nav">{entries.map(([name, suffix]) => <Link href={root + suffix} key={suffix} aria-current={active === name ? "page" : undefined}>{name}</Link>)}</nav>;
}
