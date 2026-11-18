/**
 * Android notifications for sweep days, scheduled on the phone with no server.
 *
 * The alarms are concrete one-shot notifications (`schedule.at`) for the next
 * WEEKS_AHEAD weeks, rather than the plugin's repeating `on:` form, which is
 * less reliable on Samsung's One UI. Exact alarms come from USE_EXACT_ALARM in
 * the manifest and are allowed to fire in Doze. The app resyncs the whole window
 * on launch, on resume and after every edit. A last low-priority reminder near
 * the end of the window asks you to open the app so the alarms keep going.
 *
 * In the browser (npm run dev) nothing is scheduled; test alerts just play the jingle.
 */

import { LocalNotifications, type Channel, type LocalNotificationSchema } from "@capacitor/local-notifications";

import { message, upcoming, type AlertKind, type CarView, type Rule, type Settings } from "./schedule";
import { play } from "./sound";
import { isNative } from "./storage";

export const WEEKS_AHEAD = 10;
// Android caps an app at 500 pending alarms; leave room for the test alert and reminder.
const MAX_ALERTS = 400;
const TEST_ID = 1;
const REFRESH_ID = 2;

// A channel's sound is fixed once the channel exists (Android 8+); bump the suffix if a WAV changes.
// res/raw/*_alert.wav are rendered from sound.ts by `python -m parking --export-android`.
const CHANNEL: Record<AlertKind | "refresh", string> = {
  night: "night-alert-v1",
  morning: "morning-alert-v1",
  refresh: "refresh-v1",
};
const CHANNELS: Channel[] = [
  { id: CHANNEL.night, name: "Night-before alert", description: "8 PM the evening before a sweep",
    sound: "night_alert.wav", importance: 5, visibility: 1, vibration: true },
  { id: CHANNEL.morning, name: "Sweepers-coming alert", description: "Shortly before the sweepers arrive",
    sound: "morning_alert.wav", importance: 5, visibility: 1, vibration: true },
  { id: CHANNEL.refresh, name: "Keep alerts going", description: "Reminder to open the app",
    importance: 3, visibility: 1, vibration: false },
];

/** Notification icons: the white status-bar car, and the chosen full-colour view (res/drawable-nodpi/car_large*.png). */
export function looks(view: CarView): { smallIcon: string; largeIcon: string; iconColor: string } {
  const largeIcon = view === "side" ? "car_large" : `car_large_${view}`;
  return { smallIcon: "ic_stat_car", largeIcon, iconColor: "#3b7bff" };
}

export interface PermissionInfo {
  notifications: boolean;
  exact: boolean;
}

export async function setupChannels(): Promise<void> {
  if (!isNative()) return;
  for (const channel of CHANNELS) await LocalNotifications.createChannel(channel);
}

export async function permissions(): Promise<PermissionInfo> {
  if (!isNative()) return { notifications: true, exact: true };
  const display = await LocalNotifications.checkPermissions().catch(() => ({ display: "denied" }));
  const exact = await LocalNotifications.checkExactNotificationSetting().catch(() => ({ exact_alarm: "denied" }));
  return { notifications: display.display === "granted", exact: exact.exact_alarm === "granted" };
}

export async function requestNotifications(): Promise<boolean> {
  if (!isNative()) return true;
  return (await LocalNotifications.requestPermissions()).display === "granted";
}

/** Opens Android's "Alarms & reminders" screen. */
export async function requestExact(): Promise<void> {
  if (isNative()) await LocalNotifications.changeExactNotificationSetting();
}

/** Replace every pending sweep alert with a fresh WEEKS_AHEAD-week window. Returns how many alerts are set. */
export async function resync(rules: Rule[], settings: Settings, now = new Date()): Promise<number> {
  const alerts = upcoming(rules, settings, now, WEEKS_AHEAD).slice(0, MAX_ALERTS);
  if (!isNative()) return alerts.length;

  const { exact } = await permissions();
  const pending = await LocalNotifications.getPending();
  const stale = pending.notifications.filter((n) => n.id !== TEST_ID).map((n) => ({ id: n.id }));
  if (stale.length) await LocalNotifications.cancel({ notifications: stale });
  if (!alerts.length) return 0;

  const notifications: LocalNotificationSchema[] = alerts.map((a) => ({
    id: a.id,
    ...message(a, settings),
    channelId: CHANNEL[a.kind],
    schedule: { at: a.at, allowWhileIdle: true },
    // Never let schedule() pop the settings screen mid-sync; the settings panel offers that.
    isExactNotification: exact,
    autoCancel: true,
    extra: { ruleId: a.rule.id, kind: a.kind },
    ...looks(settings.carView),
  }));

  // Four days before the window runs out, ask to be opened so the next weeks get scheduled.
  const refreshAt = new Date(now.getFullYear(), now.getMonth(), now.getDate() + WEEKS_AHEAD * 7 - 4, 12, 0);
  notifications.push({
    id: REFRESH_ID,
    title: "OPEN PIXEL PARKING",
    body: "Tap to keep your street-sweeping alerts going.",
    channelId: CHANNEL.refresh,
    schedule: { at: refreshAt, allowWhileIdle: true },
    isExactNotification: false,
    ...looks(settings.carView),
  });

  await LocalNotifications.schedule({ notifications });
  return alerts.length;
}

/** Fire a sample alert in 5 seconds (lock the phone to see it arrive). */
export async function testAlert(kind: AlertKind, view: CarView): Promise<void> {
  if (!isNative()) {
    play(kind);
    return;
  }
  const { exact } = await permissions();
  await LocalNotifications.schedule({
    notifications: [
      {
        id: TEST_ID,
        title: kind === "night" ? "MOVE YOUR CAR TONIGHT" : "SWEEPERS IN 1 HR!",
        body: "Test alert: this is what sweep days will look and sound like.",
        channelId: CHANNEL[kind],
        schedule: { at: new Date(Date.now() + 5000), allowWhileIdle: true },
        isExactNotification: exact,
        ...looks(view),
      },
    ],
  });
}
