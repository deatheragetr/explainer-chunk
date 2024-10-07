/** @type {import('tailwindcss').Config} */
export default {
  content: [],
  purge: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  darkMode: false, // or 'media' or 'class'
  theme: {
    extend: {}
  },
  plugins: [
    import('@tailwindcss/forms'),
    import('@tailwindcss/aspect-ratio'),
    import('@tailwindcss/typography')
  ]
}
