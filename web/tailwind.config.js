/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // ARIADNE control-room palette — deep slate surfaces, restrained accents.
        bg: {
          base: "#0a0e14",
          surface: "#111722",
          raised: "#161d2b",
          hover: "#1c2534",
        },
        border: {
          subtle: "#1f2937",
          DEFAULT: "#2a3646",
          strong: "#3a4a5f",
        },
        text: {
          primary: "#e6edf3",
          secondary: "#9aa7b8",
          muted: "#5e6b7e",
        },
        // semantic status language
        healthy: "#2dd4a7",
        degraded: "#f5a623",
        down: "#f45b6c",
        info: "#4f9cf9",
        accent: "#6d8bff",
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
