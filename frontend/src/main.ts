import "@fontsource/press-start-2p/400.css";
import "./styles.css";

import { App } from "@capacitor/app";

import { permissions, requestExact, requestNotifications, resync, setupChannels, testAlert } from "./notifier";
import { countdown, format12, sideLabel, upcoming, WEEKDAYS, type Rule } from "./schedule";
import { Scene } from "./scene";
import { blip } from "./sound";
import { isNative, Store, type AppData } from "./storage";
import { button, el, RuleEditor, SettingsPanel, SetupPanel, type RuleDraft } from "./ui/panels";

async function boot(): Promise<void> {
  const store = new Store();
  const data: AppData = await store.load();
  let scheduled = 0;

  // --- DOM -------------------------------------------------------------
  const app = document.getElementById("app")!;
  const hero = el("header", "hero");
  const scene = new Scene(data.settings.carView);
  const title = el("h1", "title", "PIXEL\n");
  title.style.whiteSpace = "pre";
  title.append(el("span", "", "PARKING"));
  hero.append(scene.el, title);

  const next = el("section", "card next");
  const rulesHead = el("h2", "section", "SWEEP DAYS");
  const rulesList = el("div", "rules");
  app.append(hero, next, rulesHead, rulesList);

  const editor = new RuleEditor(saveRule, deleteRule);
  const settingsPanel = new SettingsPanel(
    async (settings) => {
      data.settings = settings;
      scene.setView(settings.carView);
      await commit("Settings saved.");
    },
    () => void enableNotifications(),
    () => void requestExact(),
  );
  const setup = new SetupPanel(enableNotifications, async () => {
    data.setupDone = true;
    await store.save(data);
  });
  const panels = [editor, settingsPanel, setup];
  document.body.append(...panels.map((p) => p.el));

  const bar = el("nav", "bar");
  bar.append(
    button("+ ADD", "primary", () => editor.openWith(null, data.settings)),
    button("TEST", "", runTest),
    button("SETUP", "", async () => settingsPanel.openWith(data.settings, await permissions(), scheduled)),
  );
  document.body.append(bar);

  const toastEl = el("div", "toast");
  toastEl.hidden = true;
  document.body.append(toastEl);
  let toastTimer = 0;
  function toast(text: string): void {
    toastEl.textContent = text;
    toastEl.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => (toastEl.hidden = true), 3500);
  }

  // --- rendering -----------------------------------------------------------
  function renderNext(): void {
    const [alert] = upcoming(data.rules, data.settings, new Date(), 2);
    next.replaceChildren(el("h2", "section", "NEXT ALERT"));
    next.querySelector("h2")!.style.margin = "0";
    next.classList.toggle("empty", !alert);
    if (!alert) {
      next.append(el("div", "count", "Nothing scheduled"), el("div", "what", "Add the days your street gets swept."));
      return;
    }
    const at = alert.at;
    const hhmm = `${at.getHours()}:${String(at.getMinutes()).padStart(2, "0")}`;
    const kind = alert.kind === "night" ? "NIGHT BEFORE" : "SWEEPERS COMING";
    next.append(
      el("div", "count", `in ${countdown(at.getTime() - Date.now())}`),
      el("div", "what", `${WEEKDAYS[at.getDay()]} ${format12(hhmm)} · ${kind}`),
      el("div", "where", `${sideLabel(alert.rule.side)} SIDE · ${alert.rule.street}`),
    );
  }

  function renderRules(): void {
    const sorted = [...data.rules].sort((a, b) => a.weekday - b.weekday || a.start.localeCompare(b.start));
    rulesList.replaceChildren(
      ...sorted.map(ruleCard),
      ...(sorted.length ? [] : [el("p", "empty-rules", "No sweep days yet. Tap + ADD and enter the street, side, day and time from the sign.")]),
    );
  }

  function ruleCard(rule: Rule): HTMLElement {
    const card = el("div", `card rule${rule.enabled ? "" : " off"}`);
    const info = el("div");
    info.append(
      el("div", "street", rule.street),
      el("div", "meta", `${sideLabel(rule.side)} SIDE`),
      el("div", "meta", `${format12(rule.start)}-${format12(rule.end)}`),
    );
    const toggle = button(rule.enabled ? "ON" : "OFF", `toggle${rule.enabled ? " on" : ""}`, async () => {
      rule.enabled = !rule.enabled;
      blip();
      await commit(rule.enabled ? "Alerts on." : "Alerts paused for this rule.");
    });
    toggle.addEventListener("click", (e) => e.stopPropagation());
    card.append(el("div", "day", WEEKDAYS[rule.weekday]), info, toggle);
    card.addEventListener("click", () => editor.openWith(rule, data.settings));
    return card;
  }

  function render(): void {
    renderNext();
    renderRules();
  }

  // --- actions -------------------------------------------------------------
  async function commit(message?: string): Promise<void> {
    await store.save(data);
    render();
    try {
      scheduled = await resync(data.rules, data.settings);
      if (message) toast(message);
    } catch (err) {
      console.warn("could not schedule alerts", err);
      toast("Could not schedule alerts. Check SETUP.");
    }
  }

  async function saveRule(draft: RuleDraft, existing: Rule | null): Promise<void> {
    if (existing) Object.assign(existing, draft);
    else data.rules.push({ ...draft, id: data.nextId++ });
    blip();
    await commit(existing ? "Sweep day updated." : "Sweep day added. Alerts set!");
  }

  async function deleteRule(rule: Rule): Promise<void> {
    data.rules = data.rules.filter((r) => r.id !== rule.id);
    await commit("Sweep day deleted.");
  }

  async function enableNotifications(): Promise<void> {
    const ok = await requestNotifications();
    toast(ok ? "Alerts enabled!" : "Notifications are off. Enable them in Android settings.");
    if (ok) await commit();
  }

  async function runTest(): Promise<void> {
    scene.play();
    try {
      await testAlert("morning", data.settings.carView);
      toast(isNative() ? "Test alert in 5 seconds. Lock your phone!" : "Playing the morning alert (no notifications in the browser).");
    } catch (err) {
      console.warn("test alert failed", err);
      toast("Could not send a test alert. Check SETUP.");
    }
  }

  // --- start -------------------------------------------------------------
  render();
  void scene.load();
  window.setInterval(renderNext, 30_000);

  if (isNative()) {
    await setupChannels().catch((err) => console.warn("notification channels unavailable", err));
    await App.addListener("resume", () => void commit());
    await App.addListener("backButton", () => {
      const open = panels.find((p) => p.isOpen);
      if (open) open.close();
      else void App.minimizeApp();
    });
    if (!data.setupDone) setup.open();
  }
  await commit();
}

void boot();
