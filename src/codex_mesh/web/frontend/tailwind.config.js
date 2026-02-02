/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                bg: '#0f172a',
                sidebar: '#1e293b',
                text: '#e2e8f0',
                accent: '#3b82f6',
                border: '#334155',
            }
        },
    },
    plugins: [],
}
