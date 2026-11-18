// Run with TZ=America/New_York (see package.json) so DST dates are fixed:
// clocks fall back 2026-11-01 and spring forward 2027-03-14.
import { describe, expect, it } from "vitest";

import {
  alertId,
  alertsFor,
  countdown,
  DEFAULT_SETTINGS,
  format12,
  message,
  sideLabel,
  upcoming,
  validateRule,
  type Rule,
} from "./schedule";

const rule = (over: Partial<Rule> = {}): Rule => ({
  id: 1,
  street: "Elm St",
  side: "North",
  weekday: 1, // Monday
  start: "09:00",
  end: "11:00",
  enabled: true,
  ...over,
});

const local = (y: number, mo: number, d: number, h = 0, mi = 0) => new Date(y, mo - 1, d, h, mi);

describe("alertsFor", () => {
  it("alerts 8 PM the night before and 1 hour before a Monday sweep", () => {
    const alerts = alertsFor(rule(), DEFAULT_SETTINGS, local(2026, 11, 6, 12), 1);
    expect(alerts.map((a) => [a.kind, a.at])).toEqual([
      ["night", local(2026, 11, 8, 20)],
      ["morning", local(2026, 11, 9, 8)],
    ]);
    expect(alerts[0].sweep).toEqual(local(2026, 11, 9, 9));
  });

  it("puts a 7:00 sweep's morning alert at 6:00", () => {
    const [, morning] = alertsFor(rule({ start: "07:00", end: "09:00" }), DEFAULT_SETTINGS, local(2026, 11, 6), 1);
    expect(morning.at).toEqual(local(2026, 11, 9, 6));
  });

  it("puts a Sunday sweep's night alert on Saturday", () => {
    const [night] = alertsFor(rule({ weekday: 0 }), DEFAULT_SETTINGS, local(2026, 11, 2), 1);
    expect(night.at).toEqual(local(2026, 11, 7, 20));
    expect(night.at.getDay()).toBe(6);
  });

  it("crosses a month boundary for the night alert", () => {
    // Tuesday 2026-12-01: the night alert is Monday 2026-11-30.
    const [night] = alertsFor(rule({ weekday: 2 }), DEFAULT_SETTINGS, local(2026, 11, 28), 1);
    expect(night.at).toEqual(local(2026, 11, 30, 20));
  });

  it("skips alerts already in the past but keeps today's morning alert", () => {
    // Monday 7:30: last night's alert has passed, the 8:00 alert has not.
    const alerts = alertsFor(rule(), DEFAULT_SETTINGS, local(2026, 11, 2, 7, 30), 1);
    expect(alerts[0]).toMatchObject({ kind: "morning", at: local(2026, 11, 2, 8) });
    expect(alerts.every((a) => a.at > local(2026, 11, 2, 7, 30))).toBe(true);
  });

  it("drops today's sweep once its morning alert has passed", () => {
    const alerts = alertsFor(rule(), DEFAULT_SETTINGS, local(2026, 11, 2, 8, 30), 1);
    expect(alerts[0]).toMatchObject({ kind: "night", at: local(2026, 11, 8, 20) });
  });

  it("keeps wall-clock times across both DST changes", () => {
    const alerts = alertsFor(rule(), DEFAULT_SETTINGS, local(2026, 10, 20), 26);
    expect(alerts.length).toBe(52);
    for (const a of alerts) {
      expect([a.at.getHours(), a.at.getMinutes()]).toEqual(a.kind === "night" ? [20, 0] : [8, 0]);
    }
    // The fall-back and spring-forward Sundays are both in the window.
    const nights = alerts.filter((a) => a.kind === "night").map((a) => a.at.getTime());
    expect(nights).toContain(local(2026, 11, 1, 20).getTime());
    expect(nights).toContain(local(2027, 3, 14, 20).getTime());
  });

  it("respects custom night time and lead", () => {
    const settings = { ...DEFAULT_SETTINGS, nightTime: "21:30", leadMinutes: 90 };
    const alerts = alertsFor(rule(), settings, local(2026, 11, 6), 1);
    expect(alerts.map((a) => a.at)).toEqual([local(2026, 11, 8, 21, 30), local(2026, 11, 9, 7, 30)]);
  });

  it("skips a morning alert that would land before the night alert", () => {
    // Sweep at 00:30 with a 5-hour lead: "morning" would be 19:30 the day before, earlier than 20:00.
    const alerts = alertsFor(rule({ start: "00:30", end: "02:00" }), { ...DEFAULT_SETTINGS, leadMinutes: 300 }, local(2026, 11, 6), 1);
    expect(alerts.map((a) => a.kind)).toEqual(["night"]);
  });

  it("produces nothing for a disabled rule", () => {
    expect(alertsFor(rule({ enabled: false }), DEFAULT_SETTINGS, local(2026, 11, 2), 10)).toEqual([]);
  });

  it("gives every sweep two alerts per week over the window", () => {
    expect(alertsFor(rule(), DEFAULT_SETTINGS, local(2026, 11, 3), 10)).toHaveLength(20);
  });
});

describe("alert ids", () => {
  it("are stable whatever day the schedule is computed from", () => {
    const a = alertsFor(rule(), DEFAULT_SETTINGS, local(2026, 11, 3), 4);
    const b = alertsFor(rule(), DEFAULT_SETTINGS, local(2026, 11, 6), 4);
    const idOf = (list: typeof a, t: Date) => list.find((x) => x.at.getTime() === t.getTime())?.id;
    expect(idOf(a, local(2026, 11, 16, 8))).toBe(idOf(b, local(2026, 11, 16, 8)));
  });

  it("are unique across rules, days and kinds, and fit a 32-bit int", () => {
    const rules = [rule(), rule({ id: 2, weekday: 4 }), rule({ id: 3, weekday: 1, side: "South" })];
    const ids = upcoming(rules, DEFAULT_SETTINGS, local(2026, 11, 2), 52).map((a) => a.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(Math.max(...ids)).toBeLessThan(2 ** 31);
    expect(Math.min(...ids)).toBeGreaterThan(100);
  });

  it("differ between night and morning of the same sweep", () => {
    const day = local(2026, 11, 9);
    expect(alertId(1, day, "night")).not.toBe(alertId(1, day, "morning"));
  });
});

describe("upcoming", () => {
  it("merges rules soonest first", () => {
    const rules = [rule(), rule({ id: 2, weekday: 4, side: "South" })];
    const list = upcoming(rules, DEFAULT_SETTINGS, local(2026, 11, 2, 12), 1);
    expect(list.map((a) => a.at)).toEqual([
      local(2026, 11, 4, 20), // Wed night before Thursday
      local(2026, 11, 5, 8),
      local(2026, 11, 8, 20),
      local(2026, 11, 9, 8),
    ]);
  });
});

describe("validateRule", () => {
  it("accepts a complete rule", () => {
    expect(validateRule(rule())).toEqual([]);
  });

  it("rejects blanks and an end before the start", () => {
    expect(validateRule(rule({ street: " ", side: "", start: "11:00", end: "09:00" }))).toHaveLength(3);
    expect(validateRule(rule({ start: "", end: "" }))).toEqual(["Enter start and end times."]);
  });
});

describe("text", () => {
  it("formats 12-hour times", () => {
    expect(format12("00:05")).toBe("12:05 AM");
    expect(format12("09:00")).toBe("9:00 AM");
    expect(format12("12:30")).toBe("12:30 PM");
    expect(format12("20:00")).toBe("8:00 PM");
  });

  it("normalises the side", () => {
    expect(sideLabel("north side")).toBe("NORTH");
    expect(sideLabel(" Left ")).toBe("LEFT");
  });

  it("writes the night and morning notifications", () => {
    const [night, morning] = alertsFor(rule(), DEFAULT_SETTINGS, local(2026, 11, 6), 1);
    expect(message(night, DEFAULT_SETTINGS)).toEqual({
      title: "MOVE YOUR CAR TONIGHT",
      body: "Street sweeping tomorrow 9:00 AM-11:00 AM: no parking on the NORTH side of Elm St.",
    });
    expect(message(morning, DEFAULT_SETTINGS).title).toBe("SWEEPERS IN 1 HR!");
    expect(message(morning, { ...DEFAULT_SETTINGS, leadMinutes: 45 }).title).toBe("SWEEPERS IN 45 MIN!");
  });

  it("counts down compactly", () => {
    expect(countdown(0)).toBe("now");
    expect(countdown(20_000)).toBe("1m");
    expect(countdown(3 * 3600_000 + 12 * 60_000)).toBe("3h 12m");
    expect(countdown(2 * 86400_000 + 4 * 3600_000)).toBe("2d 4h");
  });
});
