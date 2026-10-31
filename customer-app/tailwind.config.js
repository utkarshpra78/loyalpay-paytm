/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paytm: {
          blue: '#00BAF2',
          'dark-blue': '#002970',
          'light-blue': '#E8F7FC',
          gold: '#FFB800',
        }
      }
    },
  },
  plugins: [],
}
