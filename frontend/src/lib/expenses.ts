import { expenseCategories, costTypes } from "./api/expense-types.ts";
import type { ExpenseValues } from "./api/expense-types.ts";

export function seoulPeriod(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(now);
  const part = (type: string) => parts.find((p) => p.type === type)!.value;
  const year = part("year"), month = part("month"), day = part("day");
  const last = new Date(Date.UTC(Number(year), Number(month), 0)).getUTCDate();
  return { from: `${year}-${month}-01`, to: `${year}-${month}-${last}`, today: `${year}-${month}-${day}` };
}
export function validDate(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith("0000")) return false;
  const date = new Date(value + "T00:00:00Z");
  return !Number.isNaN(date.valueOf()) && date.toISOString().slice(0, 10) === value;
}
export function expenseFormValues(form: FormData): ExpenseValues {
  const expense_date = String(form.get("expense_date") ?? "");
  const category = String(form.get("category") ?? "");
  const cost_type = String(form.get("cost_type") ?? "");
  const amount = String(form.get("amount") ?? "").trim();
  const memo = String(form.get("memo") ?? "").trim();
  if (!validDate(expense_date)) throw new Error("비용 발생일을 확인해 주세요.");
  if (!Object.hasOwn(expenseCategories, category)) throw new Error("비용 항목을 선택해 주세요.");
  if (!Object.hasOwn(costTypes, cost_type)) throw new Error("고정비 / 변동비를 직접 선택해 주세요.");
  if (!/^\d{1,18}$/.test(amount)) throw new Error("금액은 0 이상 18자리 이하의 KRW 정수로 입력해 주세요.");
  if (memo.length > 1000) throw new Error("메모는 1,000자 이하여야 합니다.");
  return { expense_date, category: category as ExpenseValues["category"],
    cost_type: cost_type as ExpenseValues["cost_type"], amount, memo: memo || null };
}
export function expenseQuery(property: string, search: Record<string, string | string[] | undefined>, now = new Date()) {
  const current = seoulPeriod(now);
  const value = (key: string) => typeof search[key] === "string" ? search[key] as string : "";
  const from = value("from") || current.from, to = value("to") || current.to;
  if (!validDate(from) || !validDate(to) || from > to) throw new Error("시작일과 종료일을 확인해 주세요.");
  const category = value("category"), cost_type = value("cost_type");
  if (category && !Object.hasOwn(expenseCategories, category)) throw new Error("비용 항목을 확인해 주세요.");
  if (cost_type && !Object.hasOwn(costTypes, cost_type)) throw new Error("비용 유형을 확인해 주세요.");
  const offset = Number(value("offset") || "0");
  if (!Number.isSafeInteger(offset) || offset < 0) throw new Error("페이지를 확인해 주세요.");
  const period = new URLSearchParams({ property_id: property, from, to });
  const list = new URLSearchParams(period);
  if (category) list.set("category", category);
  if (cost_type) list.set("cost_type", cost_type);
  list.set("limit", "50"); list.set("offset", String(offset));
  return { from, to, category, cost_type, offset, period, list };
}
export function won(value: string) { return BigInt(value).toLocaleString("ko-KR") + "원"; }
