/** Config de build Tailwind pour HistoSpec — génère un CSS statique,
 * auto-hébergé (pas de CDN), adapté à un usage en salle sans connexion
 * garantie. */
module.exports = {
  content: [
    "app/templates/**/*.html",
    "app/static/js/*.js",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        ink: "#0b0e14",
        panel: "#10141c",
        panel2: "#161b26",
        line: "#232a3a",
        ink2: "#0e1219",
        amber: { DEFAULT: "#e7a94c", dim: "#8a6a3a" },
        teal: { DEFAULT: "#4fc9b8", dim: "#2f6d64" },
        rose: { DEFAULT: "#e2687e", dim: "#7a3844" },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Consolas", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
