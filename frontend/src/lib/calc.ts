/**
 * Client-side mirror of backend/app/services/calculations.py, used by the calculator page so
 * results update instantly while typing (even while a sleeping server wakes up).
 * The backend remains the source of truth for stored sessions and exposes POST /calculate/bmr-tdee.
 */
import type { Sex } from '@/api/types';

export function bmrMifflin(sex: Sex, weightKg: number, heightCm: number, age: number): number {
  const base = 10 * weightKg + 6.25 * heightCm - 5 * age;
  return sex === 'male' ? base + 5 : base - 161;
}

export function calorieTargets(tdee: number) {
  return {
    maintenance: Math.round(tdee),
    fat_loss: Math.round(tdee - 500),
    muscle_gain: Math.round(tdee + 300),
  };
}

export function bmi(weightKg: number, heightCm: number): number {
  return weightKg / (heightCm / 100) ** 2;
}

export function bmiLabel(v: number): string {
  if (v < 18.5) return 'نقص وزن';
  if (v < 25) return 'طبيعي';
  if (v < 30) return 'زيادة وزن';
  return 'سمنة';
}
