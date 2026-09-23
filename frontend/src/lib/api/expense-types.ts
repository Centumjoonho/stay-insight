export const expenseCategories = {
  RENT: "월세", MANAGEMENT_FEE: "관리비", CLEANING: "청소비", LAUNDRY: "세탁비",
  ELECTRICITY: "전기료", GAS: "가스비", WATER: "수도료", SUPPLIES: "소모품",
  LABOR: "인건비", MARKETING: "마케팅", MAINTENANCE: "수선·유지보수",
  SUBSCRIPTION: "구독료", INSURANCE: "보험료", TAX_AND_FEE: "운영 관련 세금·공과금", OTHER: "기타",
} as const;
export const costTypes = { FIXED: "고정비", VARIABLE: "변동비" } as const;
export type ExpenseCategory = keyof typeof expenseCategories;
export type CostType = keyof typeof costTypes;
export interface ExpenseValues {
  expense_date: string; category: ExpenseCategory; cost_type: CostType; amount: string; memo: string | null;
}
export interface Expense extends ExpenseValues {
  id: string; property_id: string; organization_id: string; source: "MANUAL";
  created_by_user_id: string; created_at: string; updated_at: string;
}
export interface ExpenseSummary {
  property_id: string; from_date: string; to_date: string;
  manual_expense_total: string; fixed_expense_total: string; variable_expense_total: string;
  channel_fee_total: string; known_cost_total: string;
  category_breakdown: { category: ExpenseCategory; amount: string }[];
  cost_type_breakdown: { cost_type: CostType; amount: string }[];
  reservations_with_fee: number; reservations_missing_fee: number;
  manual_source: "MANUAL"; channel_fee_source: "owner_csv"; channel_fee_date_basis: "check_in";
  is_estimated: false;
}
