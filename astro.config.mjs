import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://mcpjunction.ai',
  trailingSlash: 'never',
  build: {
    format: 'file',
  },
  compressHTML: true,
});
