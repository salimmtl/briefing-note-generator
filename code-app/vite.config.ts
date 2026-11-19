import { fileURLToPath } from 'node:url'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import { powerApps } from '@microsoft/power-apps-vite/plugin'

const mockDataLayer = fileURLToPath(new URL('./src/mock/dataverse.mock.ts', import.meta.url))

/** `npm run dev:mock` renders the UI with sample data and no Power Apps host (local preview only). */
function mockDataverse(): Plugin {
  return {
    name: 'briefing-studio-mock-dataverse',
    enforce: 'pre',
    resolveId(source, importer) {
      if (importer && !importer.includes('dataverse.mock') && /(^|\/)dataverse$/.test(source) && source.startsWith('.')) {
        return mockDataLayer
      }
      return null
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: mode === 'mock' ? [mockDataverse(), react()] : [react(), powerApps()],
  build: {
    // pdf.js and mammoth are bundled on purpose: the code app host may block external workers and CDNs.
    chunkSizeWarningLimit: 3000,
  },
}))
