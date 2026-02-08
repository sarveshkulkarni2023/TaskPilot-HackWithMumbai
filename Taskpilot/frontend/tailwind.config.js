/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx}'
  ],
  theme: {
    extend: {
      colors: {
        ink: '#0a0b0f',
        panel: '#12141a',
        edge: '#1d2230',
        accent: '#4dd0e1',
        accent2: '#7c8cff',
        ok: '#22c55e',
        warn: '#f59e0b',
        err: '#ef4444'
      },
      boxShadow: {
        glow: '0 0 30px rgba(77, 208, 225, 0.2)'
      }
    }
  },
  plugins: []
}
