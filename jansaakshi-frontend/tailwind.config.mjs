/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    light: 'var(--primary-light)',
                    DEFAULT: '#0055ff',
                },
            },
            fontFamily: {
                outfit: ['var(--font-outfit)', 'sans-serif'],
                noto: ['var(--font-noto-devenagari)', 'sans-serif'],
            },
        },
    },
    plugins: [],
}
