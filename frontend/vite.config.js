import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { createReadStream, existsSync } from 'fs'
import { lookup } from 'mime-types'

// Serves ../docs/data/* at /data/* during `vite dev`
// so the dev server can read real data without moving files.
function serveDocsData() {
  const docsDir = path.resolve(import.meta.dirname, '../docs')
  return {
    name: 'serve-docs-data',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url?.startsWith('/data/')) return next()
        const filePath = path.join(docsDir, req.url)
        if (!existsSync(filePath)) return next()
        res.setHeader('Content-Type', lookup(filePath) || 'application/octet-stream')
        createReadStream(filePath).pipe(res)
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), serveDocsData()],
  base: './',
  build: {
    outDir: '../docs',
    emptyOutDir: false,
  },
})
