import { describe, expect, it } from "vitest";

import { looks } from "./notifier";
import { CAR_VIEWS } from "./schedule";

describe("notification icons", () => {
  it("use the picked car view for the large icon", () => {
    // res/drawable-nodpi names written by backend parking/android_art.py.
    expect(CAR_VIEWS.map((v) => looks(v.id).largeIcon)).toEqual(["car_large", "car_large_front", "car_large_rear"]);
  });

  it("always use the white silhouette in the status bar", () => {
    expect(new Set(CAR_VIEWS.map((v) => looks(v.id).smallIcon))).toEqual(new Set(["ic_stat_car"]));
  });
});
