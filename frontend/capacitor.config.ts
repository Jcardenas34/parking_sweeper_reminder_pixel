import type { CapacitorConfig } from "@capacitor/cli";

// Android shell around the Vite build (dist/). See README "Run it on Android".
const config: CapacitorConfig = {
  appId: "io.github.jcardenas34.pixelparking",
  appName: "Pixel Parking",
  webDir: "dist",
  backgroundColor: "#0a0c26",
  plugins: {
    LocalNotifications: {
      // res/drawable-*/ic_stat_car.png: white car silhouette (Android tints status-bar icons).
      smallIcon: "ic_stat_car",
      iconColor: "#3b7bff",
    },
  },
};

export default config;
