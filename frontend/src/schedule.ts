/**
 * Street-sweeping rules and the alert times they produce. Pure functions, no Capacitor.
 *
 * A rule is "no parking on <side> of <street> every <weekday>, <start>-<end>".
 * Each sweep gives two alerts:
 * - night: the evening before, at settings.nightTime (default 8:00 PM)
 * - morning: settings.leadMinutes before the sweep starts (default 1 hour)
 *
 * Times are built from local wall-clock fields (new Date(y, m, d, h, min)), so a
 * DST change moves the instant but the alert still fires at 8:00 PM on the clock.
 */

export interface Rule {
  id: number;
  street: string;
  side: string;
  /** 0 = Sunday ... 6 = Saturday, like Date.getDay(). */
  weekday: number;
  /** "HH:MM", 24-hour. */
  start: string;
  end: string;
  enabled: boolean;
}

/** Which picture of the car the app shows. Must match CAR_VIEWS in backend parking/android_art.py. */
export type CarView = "side" | "front" | "rear";
export const CAR_VIEWS: { id: CarView; label: string }[] = [
  { id: "side", label: "SIDE" },
  { id: "front", label: "FRONT" },
  { id: "rear", label: "REAR 45°" },
];

export interface Settings {
  /** "HH:MM" on the day before the sweep. */
  nightTime: string;
  /** Minutes before the sweep starts. */
  leadMinutes: number;
  /** Car picture for the header and inside notifications. */
  carView: CarView;
}

export const DEFAULT_SETTINGS: Settings = { nightTime: "20:00", leadMinutes: 60, carView: "side" };

export type AlertKind = "night" | "morning";

export interface Alert {
  /** Android notification id: stable for a given rule, sweep day and kind. */
  id: number;
  kind: AlertKind;
  at: Date;
  sweep: Date;
  rule: Rule;
}

export const WEEKDAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
export const WEEKDAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

const DAY_MS = 86_400_000;
// Ids below this are reserved for the app's own notifications (test alert, refresh reminder).
const IDS_PER_RULE = 40_000;

export function parseTime(hhmm: string): [number, number] {
  const m = /^(\d{1,2}):(\d{2})$/.exec(hhmm.trim());
  if (!m) throw new Error(`bad time "${hhmm}"`);
  const h = Number(m[1]);
  const min = Number(m[2]);
  if (h > 23 || min > 59) throw new Error(`bad time "${hhmm}"`);
  return [h, min];
}

/** "21:05" -> "9:05 PM". */
export function format12(hhmm: string): string {
  const [h, m] = parseTime(hhmm);
  const suffix = h < 12 ? "AM" : "PM";
  return `${h % 12 || 12}:${String(m).padStart(2, "0")} ${suffix}`;
}

/** "North side", "north", "N" -> "NORTH" / "N": the side without a trailing "side". */
export function sideLabel(side: string): string {
  return side.trim().replace(/\s+side$/i, "").toUpperCase() || "?";
}

/** Days since 1970-01-01 for a local calendar date (DST-proof: uses UTC of the y/m/d fields). */
function dayNumber(d: Date): number {
  return Math.round(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / DAY_MS);
}

export function alertId(ruleId: number, sweepDay: Date, kind: AlertKind): number {
  return ruleId * IDS_PER_RULE + (dayNumber(sweepDay) % (IDS_PER_RULE / 2)) * 2 + (kind === "morning" ? 1 : 0);
}

/** Problems with a rule as typed in the editor, or [] if it is fine. */
export function validateRule(rule: Omit<Rule, "id">): string[] {
  const errors: string[] = [];
  if (!rule.street.trim()) errors.push("Enter a street name.");
  if (!rule.side.trim()) errors.push("Enter which side of the street.");
  if (!(rule.weekday >= 0 && rule.weekday <= 6)) errors.push("Pick a day.");
  try {
    const [sh, sm] = parseTime(rule.start);
    const [eh, em] = parseTime(rule.end);
    if (eh * 60 + em <= sh * 60 + sm) errors.push("End time must be after the start time.");
  } catch {
    errors.push("Enter start and end times.");
  }
  return errors;
}

/** Every alert for one rule whose time is after `from`, for sweeps in the next `weeks` weeks. */
export function alertsFor(rule: Rule, settings: Settings, from: Date, weeks: number): Alert[] {
  if (!rule.enabled) return [];
  const [sh, sm] = parseTime(rule.start);
  const [nh, nm] = parseTime(settings.nightTime);
  const alerts: Alert[] = [];
  // Start at today: today's sweep may still have its morning alert ahead.
  for (let i = 0; i <= weeks * 7; i++) {
    const day = new Date(from.getFullYear(), from.getMonth(), from.getDate() + i);
    if (day.getDay() !== rule.weekday) continue;
    const sweep = new Date(day.getFullYear(), day.getMonth(), day.getDate(), sh, sm);
    const night = new Date(day.getFullYear(), day.getMonth(), day.getDate() - 1, nh, nm);
    const morning = new Date(day.getFullYear(), day.getMonth(), day.getDate(), sh, sm - settings.leadMinutes);
    if (night > from) alerts.push({ id: alertId(rule.id, day, "night"), kind: "night", at: night, sweep, rule });
    // A very long lead could put the morning alert before the night one; it would only repeat it.
    if (morning > from && morning > night) {
      alerts.push({ id: alertId(rule.id, day, "morning"), kind: "morning", at: morning, sweep, rule });
    }
  }
  return alerts;
}

/** All upcoming alerts for every enabled rule, soonest first. */
export function upcoming(rules: Rule[], settings: Settings, from: Date, weeks: number): Alert[] {
  return rules.flatMap((r) => alertsFor(r, settings, from, weeks)).sort((a, b) => a.at.getTime() - b.at.getTime());
}

/** Notification title and body for an alert. */
export function message(alert: Alert, settings: Settings): { title: string; body: string } {
  const { rule } = alert;
  const where = `the ${sideLabel(rule.side)} side of ${rule.street.trim()}`;
  const window = `${format12(rule.start)}-${format12(rule.end)}`;
  if (alert.kind === "night") {
    return {
      title: "MOVE YOUR CAR TONIGHT",
      body: `Street sweeping tomorrow ${window}: no parking on ${where}.`,
    };
  }
  const lead = settings.leadMinutes % 60 === 0 ? `${settings.leadMinutes / 60} HR` : `${settings.leadMinutes} MIN`;
  return {
    title: `SWEEPERS IN ${lead}!`,
    body: `Move off ${where} before ${format12(rule.start)} (sweeping ${window}).`,
  };
}

/** "2d 4h", "3h 12m", "7m", "now": a compact countdown for the NEXT ALERT card. */
export function countdown(ms: number): string {
  if (ms <= 0) return "now";
  const mins = Math.floor(ms / 60_000);
  const d = Math.floor(mins / 1440);
  const h = Math.floor((mins % 1440) / 60);
  const m = mins % 60;
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  return `${Math.max(1, m)}m`;
}
