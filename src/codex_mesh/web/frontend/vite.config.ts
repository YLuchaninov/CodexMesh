import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
        }
    },
    build: {
        outDir: '../static/dist',
        emptyOutDir: true,
        rollupOptions: {
            output: {
                manualChunks: (id) => {
                    if (id.includes('node_modules/mermaid')) {
                        return 'mermaid';
                    }
                    if (id.includes('Diagram') && !id.includes('node_modules')) {
                        // Bundle dynamic diagram loaders if possible
                        return 'mermaid'; // Try to force them into the same bundle
                    }
                },
            },
        },
    }
})
