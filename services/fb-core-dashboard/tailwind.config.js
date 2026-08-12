/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: '#0B0F19',
        darkLight: '#1E293B',
        accentGreen: '#10B981',
        accentRed: '#EF4444',
      }
    },
  },
  plugins: [],
}
