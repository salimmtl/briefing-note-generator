import * as pdfjs from 'pdfjs-dist'
import pdfWorkerCode from 'pdfjs-dist/build/pdf.worker.min.mjs?raw'
import mammoth from 'mammoth'

export interface ExtractionResult {
  state: 'extracted' | 'failed' | 'unsupported'
  text: string
  pageCount: number | null
  warning: string | null
  error: string | null
}

/**
 * The code app host can block workers loaded from external URLs, so the pdf.js worker is bundled inline
 * as a string and started from a Blob URL. If the host also blocks Blob workers (CSP worker-src), pdf.js
 * runs on the main thread using the bundled worker module instead.
 */
let pdfReady: Promise<void> | null = null

function probeBlobWorker(): Promise<boolean> {
  return new Promise((resolve) => {
    let worker: Worker | null = null
    const probeUrl = URL.createObjectURL(new Blob(['self.postMessage("ok")'], { type: 'text/javascript' }))
    const done = (ok: boolean) => {
      window.clearTimeout(timer)
      worker?.terminate()
      URL.revokeObjectURL(probeUrl)
      resolve(ok)
    }
    const timer = window.setTimeout(() => done(false), 3000)
    try {
      worker = new Worker(probeUrl, { type: 'module' })
      worker.onmessage = () => done(true)
      worker.onerror = () => done(false)
    } catch {
      done(false)
    }
  })
}

async function ensurePdfWorker(): Promise<void> {
  if (!pdfReady) {
    pdfReady = (async () => {
      const workerUrl = URL.createObjectURL(new Blob([pdfWorkerCode], { type: 'text/javascript' }))
      if (await probeBlobWorker()) {
        pdfjs.GlobalWorkerOptions.workerSrc = workerUrl
        return
      }
      URL.revokeObjectURL(workerUrl)
      const workerModule = await import('pdfjs-dist/build/pdf.worker.min.mjs')
      ;(globalThis as unknown as { pdfjsWorker: unknown }).pdfjsWorker = workerModule
    })()
  }
  return pdfReady
}

async function extractPdf(file: File): Promise<ExtractionResult> {
  await ensurePdfWorker()
  const data = new Uint8Array(await file.arrayBuffer())
  const task = pdfjs.getDocument({ data })
  const doc = await task.promise
  try {
    const parts: string[] = []
    for (let pageNumber = 1; pageNumber <= doc.numPages; pageNumber++) {
      const page = await doc.getPage(pageNumber)
      const content = await page.getTextContent()
      let line = ''
      const lines: string[] = []
      for (const item of content.items) {
        if (!('str' in item)) continue
        line += item.str
        if (item.hasEOL) {
          lines.push(line)
          line = ''
        }
      }
      if (line) lines.push(line)
      parts.push(`[Page ${pageNumber}]\n${lines.join('\n').trim()}`)
      page.cleanup()
    }
    const textValue = parts.join('\n\n')
    const bodyChars = textValue.replace(/\[Page \d+\]/g, '').replace(/\s+/g, '').length
    if (bodyChars < 20 * Math.max(1, doc.numPages) && bodyChars < 200) {
      return {
        state: bodyChars === 0 ? 'failed' : 'extracted',
        text: bodyChars === 0 ? '' : textValue,
        pageCount: doc.numPages,
        warning: 'This PDF has little or no text layer (probably scanned). The Writer will not be able to read it.',
        error: bodyChars === 0 ? 'No text found in the PDF.' : null,
      }
    }
    return { state: 'extracted', text: textValue, pageCount: doc.numPages, warning: null, error: null }
  } finally {
    await task.destroy()
  }
}

async function extractDocx(file: File): Promise<ExtractionResult> {
  const result = await mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() })
  const textValue = result.value.replace(/\n{3,}/g, '\n\n').trim()
  return {
    state: textValue ? 'extracted' : 'failed',
    text: textValue,
    pageCount: null,
    warning: null,
    error: textValue ? null : 'No text found in the Word document.',
  }
}

function readAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : '')
    reader.onerror = () => reject(reader.error ?? new Error('The file could not be read.'))
    reader.readAsText(file)
  })
}

export async function extractText(file: File): Promise<ExtractionResult> {
  const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  try {
    if (extension === '.pdf') return await extractPdf(file)
    if (extension === '.docx') return await extractDocx(file)
    if (extension === '.txt' || extension === '.md') {
      const textValue = (await readAsText(file)).trim()
      return {
        state: textValue ? 'extracted' : 'failed',
        text: textValue,
        pageCount: null,
        warning: null,
        error: textValue ? null : 'The file is empty.',
      }
    }
    return { state: 'unsupported', text: '', pageCount: null, warning: null, error: `${extension} files are not supported.` }
  } catch (err) {
    return {
      state: 'failed',
      text: '',
      pageCount: null,
      warning: null,
      error: err instanceof Error ? err.message : String(err),
    }
  }
}
