import { WxtVitest } from "wxt/testing";

export default {
  plugins: [WxtVitest()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./test/setup.ts"],
  },
};
