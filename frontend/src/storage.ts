/**
 * Everything the app remembers, kept on the phone: Capacitor Preferences on
 * Android (survives WebView storage eviction), localStorage in the browser.
 * Both sit behind the same small async KV interface.
 */

import { Capacitor } from "@capacitor/core";
import { Preferences } from "@capacitor/preferences";

import { DEFAULT_SETTINGS, type Rule, type Settings } from "./schedule";

export interface AppData {
  rules: Rule[];
  settings: Settings;
  nextId: number;
  /** The first-run notification/battery setup panel has been dismissed. */
  setupDone: boolean;
}

export interface KV {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
}

export const browserKV: KV = {
  async get(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  async set(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* storage unavailable: data just won't persist */
    }
  },
};

export const nativeKV: KV = {
  async get(key) {
    return (await Preferences.get({ key })).value;
  },
  async set(key, value) {
    await Preferences.set({ key, value });
  },
};

export const isNative = (): boolean => Capacitor.isNativePlatform();

const KEY = "pixel-parking";

export class Store {
  constructor(private kv: KV = isNative() ? nativeKV : browserKV) {}

  async load(): Promise<AppData> {
    let saved: Partial<AppData> = {};
    try {
      saved = JSON.parse((await this.kv.get(KEY)) ?? "{}");
    } catch {
      /* corrupt: start fresh */
    }
    const rules = Array.isArray(saved.rules) ? saved.rules : [];
    return {
      rules,
      settings: { ...DEFAULT_SETTINGS, ...saved.settings },
      nextId: Math.max(saved.nextId ?? 1, ...rules.map((r) => r.id + 1)),
      setupDone: saved.setupDone ?? false,
    };
  }

  async save(data: AppData): Promise<void> {
    await this.kv.set(KEY, JSON.stringify(data));
  }
}
