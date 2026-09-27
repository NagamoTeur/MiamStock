import { defineConfig, loadEnv } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig(({ mode }) => {
  // MIAMSTOCK_API permet de viser un backend qui n'est pas sur le port par défaut,
  // depuis l'environnement ou un fichier .env local.
  const env = loadEnv(mode, '.', 'MIAMSTOCK_');

  return {
    plugins: [svelte()],
    server: {
      port: 5273,
      // En dev, le front tourne sur Vite et l'API sur uvicorn : le proxy évite
      // toute configuration CORS, et le cookie de session reste same-origin.
      proxy: {
        '/api': {
          target: env.MIAMSTOCK_API ?? 'http://127.0.0.1:8077',
          changeOrigin: false,
        },
      },
    },
    build: {
      outDir: 'dist',
      emptyOutDir: true,
      target: 'es2022',
    },
  };
});
