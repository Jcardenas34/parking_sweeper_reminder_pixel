import {
  alertsFor,
  CAR_VIEWS,
  DEFAULT_SETTINGS,
  format12,
  validateRule,
  WEEKDAYS,
  type CarView,
  type Rule,
  type Settings,
} from "../schedule";
import { play } from "../sound";
import type { PermissionInfo } from "../notifier";

/** Element with an optional class and plain-text content (never innerHTML: street names are user text). */
export function el<K extends keyof HTMLElementTagNameMap>(tag: K, className = "", text = ""): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text) e.textContent = text;
  return e;
}

export function button(label: string, className: string, onClick: () => void): HTMLButtonElement {
  const b = el("button", `ctl ${className}`, label);
  b.type = "button";
  b.addEventListener("click", onClick);
  return b;
}

/** A centered modal panel. Only one is open at a time. */
class Panel {
  readonly el: HTMLDivElement;
  protected body: HTMLDivElement;
  protected heading: HTMLHeadingElement;

  constructor(title: string) {
    this.el = el("div", "panel");
    this.el.hidden = true;
    const box = el("div", "panel-box");
    this.heading = el("h2", "", title);
    this.body = el("div", "panel-body");
    box.append(this.heading, this.body);
    this.el.append(box);
    this.el.addEventListener("pointerdown", (e) => {
      if (e.target === this.el) this.close();
    });
  }

  get isOpen(): boolean {
    return !this.el.hidden;
  }

  open(): void {
    this.el.hidden = false;
  }

  close(): void {
    this.el.hidden = true;
  }
}

function field(label: string, ...content: HTMLElement[]): HTMLDivElement {
  const f = el("div", "field");
  f.append(el("div", "label", label), ...content);
  return f;
}

function chips(labels: string[], className = ""): { wrap: HTMLDivElement; items: HTMLButtonElement[] } {
  const wrap = el("div", `chips ${className}`);
  const items = labels.map((l) => {
    const c = el("button", "chip", l);
    c.type = "button";
    wrap.append(c);
    return c;
  });
  return { wrap, items };
}

const SIDES = ["NORTH", "SOUTH", "EAST", "WEST", "LEFT", "RIGHT", "ODD #", "EVEN #"];

export type RuleDraft = Omit<Rule, "id">;

/** Add or edit one sweep day. */
export class RuleEditor extends Panel {
  private street = el("input");
  private side = el("input");
  private start = el("input");
  private end = el("input");
  private sideChips: HTMLButtonElement[];
  private dayChips: HTMLButtonElement[];
  private preview = el("p", "preview");
  private errors = el("div", "errors");
  private deleteBtn: HTMLButtonElement;
  private weekday = 1;
  private editing: Rule | null = null;
  private settings: Settings = DEFAULT_SETTINGS;

  constructor(
    private onSave: (draft: RuleDraft, existing: Rule | null) => void,
    private onDelete: (rule: Rule) => void,
  ) {
    super("SWEEP DAY");
    this.street.type = "text";
    this.street.maxLength = 40;
    this.street.placeholder = "e.g. Elm St";
    this.side.type = "text";
    this.side.maxLength = 20;
    this.side.placeholder = "or type a side";
    for (const t of [this.start, this.end]) {
      t.type = "time";
      t.required = true;
    }

    const sides = chips(SIDES);
    this.sideChips = sides.items;
    sides.items.forEach((c) =>
      c.addEventListener("click", () => {
        this.side.value = c.textContent!.replace(" #", " numbers");
        this.refresh();
      }),
    );
    const days = chips(WEEKDAYS, "days");
    this.dayChips = days.items;
    days.items.forEach((c, i) =>
      c.addEventListener("click", () => {
        this.weekday = i;
        this.refresh();
      }),
    );
    for (const input of [this.street, this.side, this.start, this.end]) input.addEventListener("input", () => this.refresh());

    const times = el("div", "times");
    const startWrap = el("div");
    startWrap.append(el("div", "label", "START"), this.start);
    const endWrap = el("div");
    endWrap.append(el("div", "label", "END"), this.end);
    times.append(startWrap, endWrap);

    this.deleteBtn = button("DELETE", "danger", () => {
      if (this.editing && confirm(`Delete the ${WEEKDAYS[this.editing.weekday]} rule for ${this.editing.street}?`)) {
        this.onDelete(this.editing);
        this.close();
      }
    });
    const actions = el("div", "actions");
    actions.append(
      this.deleteBtn,
      el("span", "spacer"),
      button("CANCEL", "", () => this.close()),
      button("SAVE", "primary", () => this.save()),
    );

    this.body.append(
      field("STREET", this.street),
      field("NO PARKING ON SIDE", sides.wrap, this.side),
      field("SWEEP DAY (EVERY WEEK)", days.wrap),
      field("SWEEP TIME", times),
      this.preview,
      this.errors,
      actions,
    );
  }

  openWith(rule: Rule | null, settings: Settings): void {
    this.editing = rule;
    this.settings = settings;
    this.heading.textContent = rule ? "EDIT SWEEP DAY" : "NEW SWEEP DAY";
    this.street.value = rule?.street ?? "";
    this.side.value = rule?.side ?? "";
    this.weekday = rule?.weekday ?? 1;
    this.start.value = rule?.start ?? "09:00";
    this.end.value = rule?.end ?? "11:00";
    this.deleteBtn.hidden = !rule;
    this.errors.textContent = "";
    this.refresh();
    this.open();
    if (!rule) this.street.focus();
  }

  private draft(): RuleDraft {
    return {
      street: this.street.value.trim(),
      side: this.side.value.trim(),
      weekday: this.weekday,
      start: this.start.value,
      end: this.end.value,
      enabled: this.editing?.enabled ?? true,
    };
  }

  private refresh(): void {
    const side = this.side.value.trim().toUpperCase();
    this.sideChips.forEach((c) => c.classList.toggle("selected", c.textContent!.replace(" #", " NUMBERS") === side));
    this.dayChips.forEach((c, i) => c.classList.toggle("selected", i === this.weekday));
    const d = this.draft();
    if (validateRule(d).length) {
      this.preview.textContent = "";
      return;
    }
    // Show the two alerts this rule produces next week.
    const [night, morning] = alertsFor({ ...d, id: 0, enabled: true }, this.settings, new Date(Date.now() + 86_400_000), 2);
    const fmt = (dt: Date) =>
      `${WEEKDAYS[dt.getDay()]} ${format12(`${dt.getHours()}:${String(dt.getMinutes()).padStart(2, "0")}`)}`;
    this.preview.textContent = `ALERTS: ${fmt(night.at)} (night before) + ${fmt(morning.at)} (sweepers coming)`;
  }

  private save(): void {
    const d = this.draft();
    const errors = validateRule(d);
    this.errors.textContent = errors.join(" ");
    if (errors.length) return;
    this.onSave(d, this.editing);
    this.close();
  }
}

const LEADS = [30, 45, 60, 90, 120];

const CAR_THUMBS: Record<CarView, string> = {
  side: "art/car_side.png",
  front: "art/car_front.png",
  rear: "art/car_rear_quarter.png",
};

/** Alert timing, which car picture to show, sound previews, and the Android permission/battery status. */
export class SettingsPanel extends Panel {
  private night = el("input");
  private lead = el("select");
  private carView: CarView = DEFAULT_SETTINGS.carView;
  private carButtons = new Map<CarView, HTMLButtonElement>();
  private status = el("div");
  private count = el("p", "hint");

  constructor(
    private onSave: (settings: Settings) => void,
    private onFixNotifications: () => void,
    private onFixExact: () => void,
  ) {
    super("SETTINGS");
    this.night.type = "time";
    for (const m of LEADS) {
      const o = el("option", "", m % 60 ? `${m} minutes before` : `${m / 60} hour${m > 60 ? "s" : ""} before`);
      o.value = String(m);
      this.lead.append(o);
    }
    const cars = el("div", "car-picks");
    for (const { id, label } of CAR_VIEWS) {
      const b = el("button", "car-pick");
      b.type = "button";
      const img = el("img");
      img.src = CAR_THUMBS[id];
      img.alt = `${label} view of the car`;
      b.append(img, el("span", "", label));
      b.addEventListener("click", () => this.pickCar(id));
      this.carButtons.set(id, b);
      cars.append(b);
    }

    const sounds = el("div", "actions");
    sounds.style.justifyContent = "flex-start";
    sounds.append(button("♪ NIGHT", "", () => play("night")), button("♪ MORNING", "", () => play("morning")));

    const actions = el("div", "actions");
    actions.append(
      button("CANCEL", "", () => this.close()),
      button("SAVE", "primary", () => {
        this.onSave({
          nightTime: this.night.value || DEFAULT_SETTINGS.nightTime,
          leadMinutes: Number(this.lead.value),
          carView: this.carView,
        });
        this.close();
      }),
    );
    this.body.append(
      field("YOUR CAR", cars),
      field("NIGHT-BEFORE ALERT AT", this.night),
      field("SWEEPERS-COMING ALERT", this.lead),
      field("PREVIEW SOUNDS", sounds),
      this.status,
      this.count,
      batteryTip(),
      actions,
    );
  }

  openWith(settings: Settings, perms: PermissionInfo, scheduled: number): void {
    this.night.value = settings.nightTime;
    this.lead.value = String(LEADS.includes(settings.leadMinutes) ? settings.leadMinutes : 60);
    this.pickCar(settings.carView);
    this.status.replaceChildren(
      statusRow("NOTIFICATIONS", perms.notifications, () => this.onFixNotifications()),
      statusRow("EXACT ALARMS", perms.exact, () => this.onFixExact()),
    );
    this.count.textContent = `${scheduled} alerts scheduled for the next 10 weeks.`;
    this.open();
  }

  private pickCar(view: CarView): void {
    this.carView = view;
    for (const [id, b] of this.carButtons) b.classList.toggle("selected", id === view);
  }
}

function statusRow(label: string, ok: boolean, fix: () => void): HTMLDivElement {
  const row = el("div", "status");
  const text = el("span", "", `${label}: `);
  text.append(el("span", ok ? "ok" : "bad", ok ? "ON" : "OFF"));
  row.append(text);
  row.append(ok ? el("span") : button("FIX", "", fix));
  return row;
}

function batteryTip(): HTMLDivElement {
  const tip = el("div", "tip");
  tip.textContent =
    "SAMSUNG TIP: Settings > Apps > Pixel Parking > Battery > Unrestricted. " +
    "Otherwise One UI may put the app to sleep and delay alerts.";
  return tip;
}

/** First launch on the phone: allow notifications and read the battery tip. */
export class SetupPanel extends Panel {
  constructor(onEnable: () => Promise<void>, onDone: () => void) {
    super("WELCOME!");
    const intro = el(
      "p",
      "hint",
      "Pixel Parking pings you at 8 PM the night before street sweeping, and again 1 hour before the sweepers come.",
    );
    const actions = el("div", "actions");
    actions.append(
      button("ENABLE ALERTS", "primary", () => void onEnable()),
      button("GOT IT", "", () => {
        onDone();
        this.close();
      }),
    );
    this.body.append(intro, batteryTip(), actions);
  }
}
