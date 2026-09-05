/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // ARIADNE instrument substrate — graphite / blue-black, cool and deep.
        // A real elevation ladder (base -> surface -> raised -> hover), not flat slate.
        bg: {
          base: "#080a0f",
          surface: "#0d1017",
          raised: "#12161f",
          hover: "#1a1f2b",
          inset: "#05070b",
        },
        border: {
          subtle: "#171b24",
          DEFAULT: "#232a36",
          strong: "#333d4e",
        },
        text: {
          primary: "#eef2f6",
          secondary: "#8b96a6",
          muted: "#59626f",
        },
        // semantic status — communicates state, never decoration.
        healthy: "#3ad19a",
        degraded: "#f2a33c",
        down: "#f65e6e",
        info: "#5aa2f0",
        // accent = selection/focus only. A cool steel-cyan, NOT periwinkle,
        // NOT gold — it must not become the brand's primary color.
        accent: "#4db6c9",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
    },
  },
  plugins: [],
};
