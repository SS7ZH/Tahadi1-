export type Role = 'admin' | 'trainer' | 'client';
export type Sex = 'male' | 'female';
export type Goal = 'fat_loss' | 'muscle_gain' | 'fitness' | 'health' | 'performance';
export type Category = 'vital' | 'body' | 'movement' | 'physical';
export type ValueType = 'number' | 'text' | 'choice' | 'blood_pressure';
export type Direction = 'up' | 'down' | 'none';
export type Trend = 'good' | 'bad' | 'neutral';
export type QuestionStatus = 'open' | 'answered' | 'closed';

export const CATEGORIES: Category[] = ['vital', 'body', 'movement', 'physical'];

export interface ClientProfile {
  trainer_id: number | null;
  sex: Sex;
  birth_date: string | null;
  height_cm: number | null;
  goal: Goal;
  activity_key: string | null;
  notes: string | null;
}

export interface User {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
  role: Role;
  is_active: boolean;
  created_at: string;
  profile?: ClientProfile | null;
  trainer_name?: string | null;
  age?: number | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface ChoiceOption {
  value: number;
  label: string;
  label_en?: string | null;
}

export interface Definition {
  id: number;
  key: string;
  name_ar: string;
  name_en: string | null;
  category: Category;
  unit: string | null;
  unit_en: string | null;
  value_type: ValueType;
  choices: ChoiceOption[] | null;
  better_direction: Direction;
  min_value: number | null;
  max_value: number | null;
  is_active: boolean;
  sort_order: number;
}

export interface ActivityFactor {
  id: number;
  key: string;
  name_ar: string;
  name_en: string | null;
  description_ar: string | null;
  description_en: string | null;
  factor: number;
  sort_order: number;
}

export interface BloodPressure {
  systolic: number;
  diastolic: number;
}

export interface MeasurementValue {
  key: string;
  name_ar: string;
  name_en: string | null;
  category: Category;
  unit: string | null;
  unit_en: string | null;
  value_type: ValueType;
  value_number: number | null;
  value_text: string | null;
  value_json: BloodPressure | null;
  display: string;
}

export interface Comment {
  id: number;
  client_id: number;
  session_id: number | null;
  author_id: number | null;
  author_name: string | null;
  author_role: Role | null;
  body: string;
  created_at: string;
}

export interface Session {
  id: number;
  client_id: number;
  session_date: string;
  notes: string | null;
  trainer_id: number | null;
  trainer_name: string | null;
  updated_by_name: string | null;
  created_at: string;
  updated_at: string;
  values: MeasurementValue[];
  comments_count: number;
}

export interface Results {
  age: number | null;
  weight: number | null;
  height_cm: number | null;
  bmi: { value: number; category: string; label: string } | null;
  whr: { value: number; risk: string; label: string } | null;
  blood_pressure: { systolic: number; diastolic: number; category: string; label: string } | null;
  bmr: number | null;
  tdee: number | null;
  targets: { maintenance: number; fat_loss: number; muscle_gain: number } | null;
  activity: { key: string; name_ar: string; name_en: string | null; factor: number } | null;
}

export interface SessionDetail extends Session {
  results: Results;
  comments: Comment[];
}

export interface SummaryValue extends MeasurementValue {
  session_id: number;
  session_date: string;
  first_value: number | null;
  change: number | null;
  better_direction: Direction;
  trend: Trend;
  sort_order: number;
}

export interface Summary {
  client_id: number;
  sessions_count: number;
  first_session_date: string | null;
  last_session_date: string | null;
  latest_values: SummaryValue[];
  results: Results;
  bmi_change: number | null;
  bmi_trend: Trend;
}

export interface SeriesPoint {
  date: string;
  session_id: number;
  value: number;
  diastolic?: number;
}

export interface Series {
  key: string;
  name_ar: string;
  name_en: string | null;
  unit: string | null;
  unit_en: string | null;
  category: Category;
  better_direction: Direction;
  points: SeriesPoint[];
  first: number | null;
  latest: number | null;
  change: number | null;
  change_pct: number | null;
  trend: Trend;
}

export interface Progress {
  client_id: number;
  available: { key: string; name_ar: string; name_en: string | null; unit: string | null; unit_en: string | null; category: Category; derived: boolean }[];
  series: Record<string, Series>;
}

export interface ClientListItem {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
  is_active: boolean;
  sex: Sex | null;
  goal: Goal | null;
  trainer_id: number | null;
  trainer_name: string | null;
  sessions_count: number;
  last_session_date: string | null;
  weight_first: number | null;
  weight_latest: number | null;
  weight_change: number | null;
  weight_trend: Trend;
  open_questions: number;
  has_chronic: boolean;
  health_update_pending: boolean;
  subscription_end_date: string | null;
  subscription_days_left: number | null;
  subscription_status: 'active' | 'expired' | 'upcoming' | null;
}

export interface Reply {
  id: number;
  author_id: number | null;
  author_name: string | null;
  author_role: Role | null;
  body: string;
  created_at: string;
}

export interface Question {
  id: number;
  client_id: number;
  client_name: string;
  session_id: number | null;
  session_date: string | null;
  program_day_id: number | null;
  program_day_title: string | null;
  program_id: number | null;
  body: string;
  status: QuestionStatus;
  created_at: string;
  updated_at: string;
  replies: Reply[];
}

export interface AdminStats {
  trainers: number;
  clients: number;
  unassigned_clients: number;
  measurements_this_month: number;
  open_questions: number;
  recent_activity: {
    id: number;
    action: string;
    entity: string;
    entity_id: number | null;
    actor_name: string | null;
    client_name: string | null;
    timestamp: string;
  }[];
}

export interface ValueInput {
  key: string;
  value_number?: number | null;
  value_text?: string | null;
  systolic?: number | null;
  diastolic?: number | null;
}

export interface SessionInput {
  session_date: string;
  notes?: string | null;
  values: ValueInput[];
}

export interface ApiErrorBody {
  detail: string;
  code: string;
}

/* ---------------- Nutrition (calories & macros) ---------------- */
export type NutritionGoal = 'weight_loss' | 'maintenance' | 'weight_gain';
export type Macro = 'protein' | 'carbs' | 'fat';
export const MACROS: Macro[] = ['protein', 'carbs', 'fat'];

export interface MacroSettings {
  calorie_adjustment: number;
  protein_pct: number;
  carbs_pct: number;
  fat_pct: number;
  meals_min: number;
  meals_max: number;
}

export interface NutritionSettingRow extends MacroSettings {
  id: number;
  goal: NutritionGoal;
}

export interface MacroLine {
  g: number;
  kcal: number;
  pct: number;
}

export interface NutritionNumbers {
  calories: number;
  percentages: Record<Macro, number>;
  grams: Record<Macro, number>;
  macros: Record<Macro, MacroLine>;
  meals_per_day: number;
  per_meal: { calories: number } & Record<Macro, number>;
  overridden: string[];
}

export interface NutritionSuggestion extends NutritionNumbers {
  dcn: number;
  suggested_calories: number;
  meals_range: [number, number];
  settings: MacroSettings;
}

export interface NutritionPlan extends NutritionNumbers {
  id: number;
  goal: Goal;
  nutrition_goal: NutritionGoal;
  based_on_weight: number | null;
  dcn: number | null;
  suggested_calories: number | null;
  note: string | null;
  created_at: string;
  created_by_name: string | null;
}

export interface NutritionOverview {
  client_id: number;
  goal: Goal;
  nutrition_goal: NutritionGoal;
  current: NutritionPlan | null;
  suggestion: NutritionSuggestion | null;
  basis: {
    weight: number | null;
    height_cm: number | null;
    age: number | null;
    activity_factor: number | null;
    bmr: number | null;
    dcn: number | null;
    missing: string[];
  } | null;
  suggestion_changed: boolean;
  settings: Record<NutritionGoal, MacroSettings> | null;
}

export interface NutritionPlanInput {
  goal?: Goal;
  calories?: number | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  meals_per_day?: number | null;
  note?: string | null;
}

/* ---------------- Training programs ---------------- */
export type ProgramStatus = 'draft' | 'active' | 'archived';
export type ItemKind = 'resistance' | 'cardio';
export type LoadUnit = 'kg' | 'pct_1rm' | 'rpe';
export const MUSCLE_GROUPS = ['chest', 'back', 'shoulders', 'biceps', 'triceps', 'quads', 'hamstrings', 'glutes', 'calves', 'core', 'full_body', 'cardio'] as const;
export const EQUIPMENT = ['barbell', 'dumbbell', 'machine', 'cable', 'bodyweight', 'kettlebell', 'band', 'other'] as const;
export const CARDIO_TYPES = ['walking', 'running', 'cycling', 'treadmill', 'jump_rope', 'swimming', 'hiit'] as const;

export interface Exercise {
  id: number;
  name_ar: string;
  name_en: string;
  muscle_group: string;
  equipment: string | null;
  video_url: string | null;
  is_active: boolean;
}

export interface ProgramItemInput {
  kind: ItemKind;
  exercise_id?: number | null;
  custom_name?: string | null;
  muscle_group?: string | null;
  sets?: number | null;
  reps?: string | null;
  load_value?: number | null;
  load_unit?: LoadUnit | null;
  rest_seconds?: number | null;
  tempo?: string | null;
  cardio_type?: string | null;
  duration_min?: number | null;
  hr_zone?: number | null;
  speed?: number | null;
  incline?: number | null;
  work_seconds?: number | null;
  interval_rest_seconds?: number | null;
  rounds?: number | null;
  notes?: string | null;
  video_url?: string | null;
}

export interface ProgramItem extends ProgramItemInput {
  id: number;
  exercise_name_ar: string | null;
  exercise_name_en: string | null;
  hr_target: { zone: number; min_bpm: number; max_bpm: number; pct: [number, number] } | null;
}

export interface ProgramDayInput {
  day_number: number;
  week_number: number | null;
  title: string;
  is_rest: boolean;
  warmup?: string | null;
  cooldown?: string | null;
  notes?: string | null;
  items: ProgramItemInput[];
}

export interface ProgramDay extends Omit<ProgramDayInput, 'items'> {
  id: number;
  items: ProgramItem[];
}

export interface ProgramInput {
  title: string;
  goal?: string | null;
  start_date?: string | null;
  weeks: number;
  days_per_week: number;
  notes?: string | null;
  days: ProgramDayInput[];
}

export interface ProgramSummary {
  id: number;
  client_id: number | null;
  is_template: boolean;
  title: string;
  goal: string | null;
  start_date: string | null;
  weeks: number;
  days_per_week: number;
  status: ProgramStatus;
  days_count: number;
  created_at: string;
  updated_at: string;
  created_by_id: number | null;
  created_by_name: string | null;
}

export interface Program extends Omit<ProgramSummary, 'days_count'> {
  client_name: string | null;
  notes: string | null;
  activated_at: string | null;
  max_hr: number | null;
  today: {
    state: 'running' | 'not_started' | 'finished' | 'no_start_date';
    week: number | null;
    day_number: number | null;
    day_id: number | null;
    starts_in_days?: number;
  } | null;
  days: ProgramDay[];
}

/* ---------------- Onboarding, subscriptions & documents ---------------- */
export const CHRONIC_CONDITIONS = ['diabetes', 'hypertension', 'heart_disease', 'asthma', 'joint_back', 'other'] as const;
export type TemplateKind = 'contract' | 'disclaimer';

export interface Plan {
  id: number;
  name_ar: string;
  name_en: string;
  months: number;
  price: number | null;
  currency: string;
  is_active: boolean;
  sort_order: number;
}

export interface SubscriptionInfo {
  id: number;
  client_id: number;
  plan_id: number | null;
  plan_name_ar: string;
  plan_name_en: string;
  months: number;
  price: number | null;
  currency: string;
  start_date: string;
  end_date: string;
  kind: 'initial' | 'renewal' | 'change';
  status: 'active' | 'expired' | 'upcoming' | null;
  days_left: number | null;
  contract_signed: boolean | null;
  created_at: string;
}

export interface MedicalFileInfo {
  id: number;
  declaration_id: number | null;
  original_name: string;
  content_type: string;
  size_bytes: number;
  uploaded_at: string;
}

export interface HealthDeclarationInfo {
  id: number;
  has_chronic: boolean;
  conditions: string[];
  details: string | null;
  medications: string | null;
  injuries: string | null;
  created_at: string;
  reviewed_at: string | null;
  files: MedicalFileInfo[];
}

export interface SignedDocumentInfo {
  id: number;
  client_id: number;
  kind: TemplateKind;
  template_version: number;
  language: 'ar' | 'en';
  rendered_text: string;
  typed_name: string;
  signed_at: string;
  ip_address: string | null;
  subscription_id: number | null;
  health_declaration_id: number | null;
  details: Record<string, string>;
}

export interface OnboardingStatus {
  complete: boolean;
  step: 1 | 2 | 3 | null;
  steps: { subscription: boolean; health: boolean; contract: boolean };
  subscription: SubscriptionInfo | null;
  plans: Plan[];
  pending_files: MedicalFileInfo[];
  coach_name: string | null;
}

export interface RenderedTemplate {
  template_id: number;
  version: number;
  language: 'ar' | 'en';
  text: string;
  subscription?: SubscriptionInfo;
}

export interface HealthInput {
  has_chronic: boolean;
  conditions: string[];
  details?: string | null;
  medications?: string | null;
  injuries?: string | null;
  file_ids: number[];
}

export interface TemplateVersion {
  id: number;
  kind: TemplateKind;
  version: number;
  body_ar: string;
  body_en: string;
  is_active: boolean;
  created_at: string;
  created_by_name: string | null;
}

/* ---------------- Public site content ---------------- */
export const HOME_FEATURE_KEYS = ['measurements', 'programs', 'nutrition', 'reports', 'questions'] as const;

export interface HomeFeature {
  key: (typeof HOME_FEATURE_KEYS)[number];
  title_ar: string;
  title_en: string;
  text_ar: string;
  text_en: string;
}

export interface HomeContent {
  hero_title_ar: string;
  hero_title_en: string;
  hero_text_ar: string;
  hero_text_en: string;
  features: HomeFeature[];
  contact: { phone: string; whatsapp: string; email: string };
}
