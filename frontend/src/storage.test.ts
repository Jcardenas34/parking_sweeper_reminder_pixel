import { describe, expect, it } from "vitest";

import { DEFAULT_SETTINGS } from "./schedule";
import { Store, type KV } from "./storage";

function memoryKV(initial: Record<string, string> = {}): KV {
  const data = { ...initial };
  return {
    async get(k) {
      return data[k] ?? null;
    },
    async set(k, v) {
      data[k] = v;
    },
  };
}

describe("Store", () => {
  it("starts empty with default settings", async () => {
    expect(await new Store(memoryKV()).load()).toEqual({
      rules: [],
      settings: DEFAULT_SETTINGS,
      nextId: 1,
      setupDone: false,
    });
  });

  it("round-trips rules and settings", async () => {
    const store = new Store(memoryKV());
    const rule = { id: 4, street: "Elm St", side: "North", weekday: 1, start: "09:00", end: "11:00", enabled: true };
    await store.save({ rules: [rule], settings: { nightTime: "21:00", leadMinutes: 45, carView: "rear" }, nextId: 5, setupDone: true });
    expect(await store.load()).toEqual({
      rules: [rule],
      settings: { nightTime: "21:00", leadMinutes: 45, carView: "rear" },
      nextId: 5,
      setupDone: true,
    });
  });

  it("never reuses a rule id and survives corrupt data", async () => {
    const rule = { id: 9, street: "A", side: "N", weekday: 2, start: "08:00", end: "10:00", enabled: true };
    const kv = memoryKV({ "pixel-parking": JSON.stringify({ rules: [rule], nextId: 3 }) });
    expect((await new Store(kv).load()).nextId).toBe(10);
    expect((await new Store(memoryKV({ "pixel-parking": "{oops" })).load()).rules).toEqual([]);
  });
});

describe("car view setting", () => {
  it("defaults to the side view for data saved before the setting existed", async () => {
    const old = { rules: [], settings: { nightTime: "20:00", leadMinutes: 60 }, nextId: 1, setupDone: true };
    const kv = memoryKV({ "pixel-parking": JSON.stringify(old) });
    expect((await new Store(kv).load()).settings.carView).toBe("side");
  });
});
