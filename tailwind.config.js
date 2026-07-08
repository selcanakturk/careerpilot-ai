/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef8ff',
          100: '#d8efff',
          500: '#1283c7',
          600: '#0b6aa8',
          700: '#095886',
        },
        ink: '#102033',
      },
      boxShadow: {
        soft: '0 18px 55px rgba(15, 23, 42, 0.08)',
      },
    },
  },
  plugins: [],
};
