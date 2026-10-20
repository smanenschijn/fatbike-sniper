import { defineConfig } from 'vite';

// Relative base so the build works from any path.
export default defineConfig({
  base: './',
  build: { chunkSizeWarningLimit: 1200 },
});
