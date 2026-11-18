/**
 * The header: the night street with the car parked at the kerb, drawn on a
 * canvas at art resolution (160x72) and scaled up with crisp pixels.
 *
 * The car is whichever view the user picked (settings.carView). On TEST, the side
 * view drives off to the right and back round to its spot with its wheels spinning;
 * the front and rear views bounce on their springs instead.
 */

import type { CarView } from "./schedule";

const W = 160;
const H = 72;
// Matches backend parking/imaging/street.py: kerb at 68% down.
const CURB_Y = Math.round(H * 0.68);
// Side sheet: three 64x24 frames, tires 3 rows into the road (CAR_ABOVE_CURB = 19).
const SIDE_W = 64;
const SIDE_H = 24;
const SIDE_Y = CURB_Y - 19;
// Front and rear stand a few rows out in the road, as in android_art.large_icon().
// Must match HEADER_STAND_BOTTOM in backend parking/android_art.py.
const STAND_BOTTOM = CURB_Y + 8;
const DRIVE_MS = 2600;
const BOUNCE_MS = 1200;

const SOURCES: Record<CarView, string> = {
  side: "art/car_sheet.png",
  front: "art/car_front.png",
  rear: "art/car_rear_quarter.png",
};
// The rear view gets a street drawn from its own 45° angle (backend street.street_rear),
// laid out for the car exactly where draw() puts it: centred, rounding down, its lowest
// pixel on STAND_BOTTOM. The side and front views share the flat street.
const STREETS: Record<CarView, string> = {
  side: "art/street.png",
  front: "art/street.png",
  rear: "art/street_rear.png",
};

function load(src: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

export class Scene {
  readonly el: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private streets: Partial<Record<CarView, HTMLImageElement | null>> = {};
  private cars: Partial<Record<CarView, HTMLImageElement | null>> = {};
  private animStart = 0;

  constructor(private view: CarView) {
    this.el = document.createElement("canvas");
    this.el.className = "scene";
    this.el.width = W;
    this.el.height = H;
    this.ctx = this.el.getContext("2d")!;
    this.ctx.imageSmoothingEnabled = false;
  }

  async load(): Promise<void> {
    const views = Object.keys(SOURCES) as CarView[];
    const srcs = [...new Set(Object.values(STREETS))];
    const [streetImgs, cars] = await Promise.all([
      Promise.all(srcs.map(load)),
      Promise.all(views.map((v) => load(SOURCES[v]))),
    ]);
    views.forEach((v, i) => {
      this.streets[v] = streetImgs[srcs.indexOf(STREETS[v])];
      this.cars[v] = cars[i];
    });
    this.draw(0, 0, 0);
  }

  setView(view: CarView): void {
    this.view = view;
    if (!this.animStart) this.draw(0, 0, 0);
  }

  /** The TEST animation for the current view. */
  play(): void {
    if (this.animStart) return;
    this.animStart = performance.now();
    const ms = this.view === "side" ? DRIVE_MS : BOUNCE_MS;
    const step = (t: number) => {
      const p = Math.min(1, (t - this.animStart) / ms);
      if (this.view === "side") {
        // Ease out of the spot, loop round the screen, ease back in.
        const eased = p < 0.5 ? 2 * p * p : 1 - (-2 * p + 2) ** 2 / 2;
        this.draw(eased * (W + SIDE_W), 0, p < 1 ? 1 + (Math.floor(t / 90) % 2) : 0);
      } else {
        // Three hops, each smaller than the last.
        const hop = Math.abs(Math.sin(p * Math.PI * 3)) * 4 * (1 - p);
        this.draw(0, -Math.round(hop), 0);
      }
      if (p < 1) requestAnimationFrame(step);
      else this.animStart = 0;
    };
    requestAnimationFrame(step);
  }

  /** dx: how far the side view has driven from its spot; dy: lift; frame: side sheet frame. */
  private draw(dx: number, dy: number, frame: number): void {
    const { ctx } = this;
    ctx.clearRect(0, 0, W, H);
    const street = this.streets[this.view];
    if (street) ctx.drawImage(street, 0, 0);
    const car = this.cars[this.view];
    if (!car) return;
    if (this.view === "side") {
      const span = W + SIDE_W;
      const x = ((((W - SIDE_W) / 2 + dx + SIDE_W) % span) + span) % span - SIDE_W;
      ctx.drawImage(car, frame * SIDE_W, 0, SIDE_W, SIDE_H, Math.round(x), SIDE_Y, SIDE_W, SIDE_H);
    } else {
      ctx.drawImage(car, Math.floor((W - car.width) / 2), STAND_BOTTOM - car.height + dy);
    }
  }
}
