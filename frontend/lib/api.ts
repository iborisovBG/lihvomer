/**
 * Празен низ значи „същият адрес" — в продукция nginx обслужва и двете на
 * един домейн, затова относителните пътища са правилният избор.
 *
 * Локалната разработка задава пълния адрес в `.env.local`, защото там
 * фронтендът и API-то са на различни портове. Обратното — резервна стойност
 * с localhost — води до счупена продукция: Next.js изхвърля празните
 * променливи при вграждане и оставя localhost в публичния пакет.
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

const TOKEN_KEY = "lihvomer_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      0,
      "Няма връзка със сървъра. Проверете дали бекендът е стартиран на " +
        API_BASE,
    );
  }

  if (response.status === 204) return undefined as T;

  const body = await response.text();
  const parsed = body ? JSON.parse(body) : null;

  if (!response.ok) {
    const detail = parsed?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg: string }) => d.msg).join("; ")
          : `Заявката се провали (${response.status}).`;
    throw new ApiError(response.status, message);
  }

  return parsed as T;
}

// --- Типове, огледални на Pydantic схемите ---------------------------------

export type Signal = "TAKE" | "NEUTRAL" | "WAIT";
export type LoanType = "MORTGAGE" | "CONSUMER";
export type Currency = "BGN" | "EUR";
export type IndexType =
  | "EURIBOR_3M"
  | "EURIBOR_6M"
  | "EURIBOR_12M"
  | "BLP"
  | "FIXED";

export interface ScoreComponent {
  value: number;
  points: number;
  weight: number;
  label_bg: string;
  explanation_bg: string;
}

export interface Score {
  score: number;
  signal: Signal;
  signal_label_bg: string;
  headline_bg: string;
  real_rate: number;
  bund_momentum_60d: number;
  sentiment_score: number | null;
  components: Record<string, ScoreComponent>;
  computed_at: string;
}

export interface MacroIndicator {
  code: string;
  name_bg: string;
  plain_bg: string;
  unit: string;
  frequency: string;
  latest_date: string | null;
  latest_value: number | null;
  previous_value: number | null;
  change: number | null;
  source: string;
  source_ref: string;
  last_ingested_at: string | null;
  spark: number[];
}

export interface LiveDashboard {
  generated_at: string;
  indicators: MacroIndicator[];
  real_mortgage_rate_pct: number | null;
  score: Score | null;
}

export interface SeriesPoint {
  date: string;
  value: number;
}

export interface ForecastPoint {
  horizon_days: number;
  target_date: string;
  predicted_value: number;
  ci_lower: number;
  ci_upper: number;
}

export interface Forecast {
  target_series_code: string;
  driver_series_code: string;
  best_lag_days: number;
  n_obs: number;
  r_squared: number;
  adj_r_squared: number;
  diagnostics: Record<string, unknown>;
  latest_actual_date: string;
  latest_actual_value: number;
  points: ForecastPoint[];
  history: SeriesPoint[];
  driver_history: SeriesPoint[];
  explanation_bg: string;
}

export interface Loan {
  id: number;
  label: string;
  bank_name: string;
  loan_type: LoanType;
  currency: Currency;
  principal_amount: number;
  remaining_months: number;
  current_interest_rate: number;
  index_type: IndexType;
  margin: number | null;
  next_reset_date: string | null;
  created_at: string;
  updated_at: string;
}

export type LoanInput = Omit<Loan, "id" | "created_at" | "updated_at">;

export interface LoanHorizon {
  horizon_days: number;
  target_date: string;
  projected_rate_pct: number;
  projected_monthly_payment: number;
  delta_monthly: number;
  delta_monthly_eur: number;
  ci_lower_payment: number;
  ci_upper_payment: number;
}

export interface LoanProjection {
  loan_id: number;
  label: string;
  bank_name: string;
  currency: Currency;
  current_rate_pct: number;
  current_monthly_payment: number;
  horizons: LoanHorizon[];
  total_interest_remaining: number;
  explanation_bg: string;
  rate_consistency_warning_bg: string | null;
}

export interface AmortizationRow {
  month: number;
  payment: number;
  interest: number;
  principal: number;
  balance: number;
}

export interface CalculatorResult {
  monthly_payment: number;
  total_paid: number;
  total_interest: number;
  apr_pct: number;
  schedule: AmortizationRow[];
}

export interface BankQuote {
  bank_name: string;
  product_name: string;
  index_type: IndexType;
  index_value_pct: number | null;
  margin_pct: number;
  nominal_rate_pct: number;
  monthly_payment: number;
  monthly_fee: number;
  monthly_insurance: number;
  total_monthly_cost: number;
  upfront_fees: number;
  total_cost: number;
  total_interest: number;
  apr_pct: number;
  ltv_pct: number | null;
  real_monthly_payment_end_of_term: number;
  source_url: string;
  rate_effective_date: string;
  disqualified_reason: string | null;
}

export interface CompareResult {
  generated_at: string;
  amount: number;
  months: number;
  currency: Currency;
  inflation_bg_pct: number | null;
  index_values: Record<string, number>;
  market_average_rate_pct: number | null;
  market_average_note_bg: string;
  quotes: BankQuote[];
}


export type NewsImpact = "FAVOURABLE" | "NEUTRAL" | "UNFAVOURABLE";
export type SpreadStatus = "CALM" | "WATCH" | "ALERT" | "UNKNOWN";

export interface SpreadPoint {
  period: string;
  bg_yield: number;
  de_yield: number;
  spread_bp: number;
}

export interface Fiscal {
  debt_pct_gdp: number | null;
  debt_period: string | null;
  debt_is_quarterly: boolean;
  debt_limit_pct: number;
  deficit_pct_gdp: number | null;
  deficit_period: string | null;
  deficit_is_quarterly: boolean;
  deficit_limit_pct: number;
  exceeds_deficit_limit: boolean;
  exceeds_debt_limit: boolean;
  spread_latest_bp: number | null;
  spread_period: string | null;
  spread_status: SpreadStatus;
  spread_watch_bp: number;
  spread_alert_bp: number;
  spread_history: SpreadPoint[];
  explanation_bg: string;
}

export interface SpendingLine {
  cofog_code: string;
  label_bg: string;
  pct_gdp: number;
  share_of_total_pct: number;
  is_detail: boolean;
}

export interface Spending {
  period: string;
  total_pct_gdp: number;
  lines: SpendingLine[];
  source_ref: string;
  explanation_bg: string;
}

export interface NewsItem {
  id: number;
  source_code: string;
  source_name: string;
  url: string;
  language: string;
  title_bg: string;
  title_original: string;
  summary_bg: string | null;
  was_translated: boolean;
  published_at: string;
  sentiment_score: number;
  impact: NewsImpact;
  wallet_explanation_bg: string;
  is_bulgaria_related: boolean;
}

export interface NewsFeed {
  generated_at: string;
  aggregate_sentiment: number | null;
  aggregate_label_bg: string;
  translator_available: boolean;
  items: NewsItem[];
}

export interface Freshness {
  code: string;
  name_bg: string;
  latest_date: string | null;
  age_days: number | null;
  expected_max_age_days: number;
  is_stale: boolean;
  superseded_by: string | null;
  source: string;
}


export interface SourceSeries {
  code: string;
  name_bg: string;
  plain_bg: string;
  frequency: string;
  source_ref: string;
  browse_url: string;
  latest_date: string | null;
  superseded_by: string | null;
}

export interface SourceProvider {
  key: string;
  name_bg: string;
  description_bg: string;
  portal_url: string;
  api_base_url: string;
  licence_bg: string;
  series: SourceSeries[];
}

export interface NewsFeedSource {
  code: string;
  name_bg: string;
  url: string;
  language: string;
}

export interface Sources {
  generated_at: string;
  providers: SourceProvider[];
  news_feeds: NewsFeedSource[];
  disclaimer_bg: string;
}


export interface Partner {
  key: string;
  name: string;
  url: string;
  role_bg: string;
  what_they_do_bg: string;
  disclosure_bg: string;
  good_fit_bg: string[];
}

export interface Partners {
  partners: Partner[];
  general_note_bg: string;
}

export interface JobRun {
  job_name: string;
  status: "RUNNING" | "SUCCESS" | "PARTIAL" | "FAILED";
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  items_ok: number;
  items_failed: number;
}

export interface Automation {
  generated_at: string;
  worker_online: boolean;
  schedule_bg: Record<string, string>;
  last_runs: JobRun[];
  hint_bg: string;
}


export interface MarketComparison {
  your_rate_pct: number;
  market_rate_pct: number;
  market_period: string;
  difference_pp: number;
  is_above_market: boolean;
  monthly_difference: number;
  remaining_term_difference: number;
  verdict_bg: string;
}

export interface Refinance {
  new_rate_pct: number;
  new_monthly_payment: number;
  monthly_saving: number;
  upfront_cost: number;
  break_even_month: number | null;
  total_saving_over_term: number;
  is_worth_it: boolean;
  verdict_bg: string;
}

export interface EarlyRepayment {
  extra_monthly: number;
  months_saved: number;
  interest_saved: number;
  new_term_months: number;
  verdict_bg: string;
}

export interface LoanHealth {
  loan_id: number;
  label: string;
  bank_name: string;
  currency: Currency;
  principal_amount: number;
  remaining_months: number;
  current_monthly_payment: number;
  market: MarketComparison;
  refinance: Refinance;
  early_repayment: EarlyRepayment[];
  refinance_cost_note_bg: string;
}

export interface Savings {
  amount: number;
  deposit_rate_pct: number;
  deposit_kind_bg: string;
  inflation_pct: number;
  inflation_period: string;
  real_rate_pct: number;
  annual_loss: number;
  five_year_loss: number;
  verdict_bg: string;
}


export type NotificationKind =
  | "PAYMENT_CHANGE"
  | "RESET_APPROACHING"
  | "ABOVE_MARKET";
export type NotificationSeverity = "INFO" | "WARNING" | "OPPORTUNITY";

export interface AppNotification {
  id: number;
  loan_id: number | null;
  kind: NotificationKind;
  severity: NotificationSeverity;
  title_bg: string;
  body_bg: string;
  action_bg: string | null;
  created_at: string;
  read_at: string | null;
  emailed_at: string | null;
}

export interface NotificationFeed {
  unread_count: number;
  email_delivery_enabled: boolean;
  items: AppNotification[];
}

export interface Preferences {
  notify_email: boolean;
  notify_push: boolean;
  alert_threshold_eur: number;
  risk_tolerance: "CONSERVATIVE" | "BALANCED" | "AGGRESSIVE";
}

export interface Waiting {
  target_price: number;
  down_payment_pct: number;
  saved_now: number;
  monthly_saving: number;
  house_growth_pct: number;
  house_growth_period: string;
  house_growth_is_observed: boolean;
  deposit_rate_pct: number;
  needed_now: number;
  gap_now: number;
  months_to_afford: number | null;
  needed_in_year: number;
  saved_in_year: number;
  gap_in_year: number;
  cost_of_one_year: number;
  gap_is_widening: boolean;
  verdict_bg: string;
  assumption_note_bg: string;
}

export interface OfferVerdict {
  amount: number;
  months: number;
  nominal_rate_pct: number;
  monthly_payment: number;
  monthly_fee: number;
  monthly_insurance: number;
  total_monthly_cost: number;
  upfront_fee: number;
  offer_aprc_pct: number;
  market_aprc_pct: number;
  market_period: string;
  difference_pp: number;
  is_above_market: boolean;
  monthly_difference: number;
  total_difference: number;
  hidden_cost_pp: number;
  verdict_bg: string;
  hidden_cost_note_bg: string;
}

// --- Извиквания -------------------------------------------------------------






export const api = {
  register: (email: string, password: string) =>
    request<{ access_token: string }>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  dashboard: () => request<LiveDashboard>("/api/v1/macro/live-dashboard"),

  forecast: (target?: string) =>
    request<Forecast>(
      `/api/v1/forecast/mortgage-rates${target ? `?target=${target}` : ""}`,
    ),

  loans: () => request<Loan[]>("/api/v1/user/loans"),

  createLoan: (payload: LoanInput) =>
    request<Loan>("/api/v1/user/loans", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateLoan: (id: number, payload: LoanInput) =>
    request<Loan>(`/api/v1/user/loans/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  deleteLoan: (id: number) =>
    request<void>(`/api/v1/user/loans/${id}`, { method: "DELETE" }),

  projections: () => request<LoanProjection[]>("/api/v1/user/loans/projections"),

  calculate: (payload: {
    amount: number;
    months: number;
    annual_rate_pct: number;
    monthly_fee: number;
    upfront_fee: number;
  }) =>
    request<CalculatorResult>("/api/v1/calculator/payment", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  compareBanks: (payload: {
    amount: number;
    months: number;
    loan_type: LoanType;
    currency: Currency;
    property_value?: number | null;
    sort_by: "apr" | "monthly_payment" | "total_cost";
  }) =>
    request<CompareResult>("/api/v1/calculator/compare-banks", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  fiscal: () => request<Fiscal>("/api/v1/fiscal/overview"),

  spending: () => request<Spending>("/api/v1/fiscal/spending"),

  news: (bulgariaOnly = false, limit = 40) =>
    request<NewsFeed>(
      `/api/v1/news/translated-sentiment?limit=${limit}&bulgaria_only=${bulgariaOnly}`,
    ),

  freshness: () => request<Freshness[]>("/api/v1/macro/freshness"),

  sources: () => request<Sources>("/api/v1/macro/sources"),

  partners: () => request<Partners>("/api/v1/partners"),

  automation: () => request<Automation>("/api/v1/system/automation"),

  loanHealth: (refinanceCost = 0) =>
    request<LoanHealth[]>(
      `/api/v1/advice/loan-health?refinance_cost=${refinanceCost}`,
    ),

  savings: (amount: number, useTermDeposit: boolean) =>
    request<Savings>("/api/v1/advice/savings", {
      method: "POST",
      body: JSON.stringify({ amount, use_term_deposit: useTermDeposit }),
    }),

  notifications: (unreadOnly = false) =>
    request<NotificationFeed>(
      `/api/v1/notifications?unread_only=${unreadOnly}`,
    ),

  markRead: (id: number) =>
    request<AppNotification>(`/api/v1/notifications/${id}/read`, {
      method: "POST",
    }),

  markAllRead: () =>
    request<NotificationFeed>("/api/v1/notifications/read-all", {
      method: "POST",
    }),

  checkNow: () =>
    request<NotificationFeed>("/api/v1/notifications/check-now", {
      method: "POST",
    }),

  me: () =>
    request<{ id: number; email: string } & Preferences>("/api/v1/auth/me"),

  savePreferences: (payload: Preferences) =>
    request<Preferences>("/api/v1/notifications/preferences", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  costOfWaiting: (payload: {
    target_price: number;
    down_payment_pct: number;
    saved_now: number;
    monthly_saving: number;
    house_growth_pct: number | null;
  }) =>
    request<Waiting>("/api/v1/advice/cost-of-waiting", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  evaluateOffer: (payload: {
    amount: number;
    months: number;
    loan_type: LoanType;
    nominal_rate_pct: number;
    monthly_fee: number;
    upfront_fee: number;
    property_insurance_annual_pct: number;
    life_insurance_annual_pct: number;
  }) =>
    request<OfferVerdict>("/api/v1/advice/evaluate-offer", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
