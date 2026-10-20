import { fileURLToPath, URL } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  // On Vercel the API URL is baked in at build time; building without it would silently
  // point the deployed site at localhost.
  if (process.env.VERCEL && !env.VITE_API_URL) {
    throw new Error(
      'VITE_API_URL is not set. Add it in Vercel → Project Settings → Environment Variables ' +
        '(e.g. https://tahadi.onrender.com/api/v1) and redeploy.',
    );
  }

  return {
    plugins: [react()],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: { port: 5173 },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            react: ['react', 'react-dom', 'react-router-dom'],
            charts: ['recharts'],
          },
        },
      },
    },
  };
});
