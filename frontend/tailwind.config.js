/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#FAF8F5",
        card: "#FFFFFF",
        "card-soft": "#F6F1EC",
        primary: "#9CAF88",
        "primary-soft": "#E8EEE2",
        text: "#3A3530",
        muted: "#8A8176",
        border: "#EAE3D9",
        positive: "#7FA876",
        negative: "#D98888",
      },
      borderRadius: {
        DEFAULT: "8px",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
