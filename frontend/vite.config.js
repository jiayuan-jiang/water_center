import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { createReadStream, existsSync, cpSync } from 'fs'
import { lookup } from 'mime-types'

// Dev: serves ../docs/data/* at /data/*
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

// Build: copies ../docs/data/ → dist/data/
function copyDocsData() {
  const src  = path.resolve(import.meta.dirname, '../docs/data')
  const dest = path.resolve(import.meta.dirname, 'dist/data')
  return {
    name: 'copy-docs-data',
    closeBundle() {
      cpSync(src, dest, { recursive: true })
    },
  }
}

export default defineConfig({
  plugins: [react(), serveDocsData(), copyDocsData()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})