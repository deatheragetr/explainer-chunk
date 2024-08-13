import * as XLSX from 'xlsx'
import * as Papa from 'papaparse'
import * as pdfjs from 'pdfjs-dist'
import ePub from 'epubjs'
import * as mammoth from 'mammoth'
import type { Ref } from 'vue'
import type { ImportProgress, ExtractionResult } from '@/types'
import type Spine from 'epubjs/types/spine'

class UnsupportedFileTypeError extends Error {
  constructor(fileType: string) {
    super(`Unsupported file type: ${fileType}`)
    this.name = 'UnsupportedFileTypeError'
  }
}

type ProgressUpdater = (
  status: string,
  progress: number,
  payload?: Partial<ImportProgress['payload']>
) => void

async function extractTextFromFile(
  file: File,
  importProgress: Ref<ImportProgress | null>
): Promise<ExtractionResult> {
  const fileType = file.type
  const updateProgress: ProgressUpdater = (status, progress, payload = {}) => {
    if (importProgress.value) {
      importProgress.value = {
        ...importProgress.value,
        status,
        progress,
        payload: { ...importProgress.value.payload, ...payload }
      }
    }
  }

  const extractors: Record<
    string,
    (file: File, updateProgress: ProgressUpdater) => Promise<ExtractionResult>
  > = {
    'application/pdf': extractFromPDF,
    'application/epub+zip': extractFromEPUB,
    'application/json': extractFromJSON,
    'text/markdown': extractFromTextFile,
    'text/plain': extractFromTextFile,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': extractFromDOCX,
    'text/csv': extractFromCSV,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': extractFromXLSX
  }

  const extractor = extractors[fileType]
  if (!extractor) {
    throw new UnsupportedFileTypeError(fileType)
  }

  updateProgress('initializing', 0, { file_type: fileType })

  try {
    const result = await extractor(file, updateProgress)
    updateProgress('completed', 100)
    return result
  } catch (error) {
    updateProgress('error', 0)
    console.error(`Error extracting text from ${fileType} file:`, error)
    throw error
  }
}

async function extractFromPDF(
  file: File,
  updateProgress: ProgressUpdater
): Promise<ExtractionResult> {
  updateProgress('loading PDF', 10)
  const arrayBuffer = await file.arrayBuffer()
  const pdf = await pdfjs.getDocument(arrayBuffer).promise
  let text = ''
  const metadata: Record<string, any> = {}

  updateProgress('extracting text', 20)
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i)
    const content = await page.getTextContent()
    text += content.items.map((item: any) => item.str).join(' ') + '\n'
    updateProgress('extracting text', 20 + (70 * i) / pdf.numPages)
  }

  updateProgress('fetching metadata', 90)
  const info = await pdf.getMetadata()
  if (info?.info) {
    metadata.title = info.info.Title
    metadata.author = info.info.Author
    metadata.subject = info.info.Subject
    metadata.keywords = info.info.Keywords
  }

  return { text, metadata }
}
async function extractFromEPUB(
  file: File,
  updateProgress: ProgressUpdater
): Promise<ExtractionResult> {
  return new Promise((resolve, reject) => {
    updateProgress('loading EPUB', 10)
    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        const arrayBuffer = e.target?.result as ArrayBuffer
        const book = ePub(arrayBuffer)

        updateProgress('extracting metadata', 30)
        const metadata = await book.loaded.metadata

        updateProgress('extracting content', 50)
        let text = ''

        await book.ready

        const spine: Spine = book.spine
        const spineItems = spine.items

        for (let i = 0; i < spineItems.length; i++) {
          const item = spineItems[i]
          if (item && item.href) {
            const section = await book.spine.get(item.href)
            if (section) {
              const content = await section.load(book.load.bind(book))
              text += extractTextFromContent(content) + '\n'
            }
          }
          updateProgress('extracting content', 50 + (40 * (i + 1)) / spineItems.length)
        }

        resolve({
          text,
          metadata: {
            title: metadata.title,
            creator: metadata.creator,
            publisher: metadata.publisher
          }
        })
      } catch (error) {
        console.error('Error processing EPUB:', error)
        reject(error)
      }
    }
    reader.onerror = reject
    reader.readAsArrayBuffer(file)
  })
}

function extractTextFromContent(content: any): string {
  if (typeof content === 'string') {
    // If content is a string, assume it's HTML and parse it
    const parser = new DOMParser()
    const doc = parser.parseFromString(content, 'text/html')
    return extractTextFromNode(doc.body)
  } else if (content && typeof content === 'object') {
    // If content is an object, it might be a custom structure from epubjs
    // Try to extract text from common properties
    let text = ''
    if (content.textContent) {
      text += content.textContent + ' '
    }
    if (content.innerText) {
      text += content.innerText + ' '
    }
    if (content.innerHTML) {
      const parser = new DOMParser()
      const doc = parser.parseFromString(content.innerHTML, 'text/html')
      text += extractTextFromNode(doc.body) + ' '
    }
    if (Array.isArray(content.childNodes)) {
      text += content.childNodes.map((node: any) => extractTextFromContent(node)).join(' ')
    }
    return text.trim()
  }
  return ''
}

function extractTextFromNode(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.textContent?.trim() || ''
  }

  if (node.nodeType === Node.ELEMENT_NODE) {
    return Array.from(node.childNodes)
      .map((child) => extractTextFromNode(child))
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim()
  }

  return ''
}

async function extractFromJSON(
  file: File,
  updateProgress: ProgressUpdater
): Promise<ExtractionResult> {
  updateProgress('reading JSON', 20)
  const text = await file.text()
  updateProgress('parsing JSON', 60)
  const parsed = JSON.parse(text)
  return {
    text: JSON.stringify(parsed, null, 2),
    metadata: {
      topLevelKeys: Object.keys(parsed)
    }
  }
}

async function extractFromTextFile(
  file: File,
  updateProgress: ProgressUpdater
): Promise<ExtractionResult> {
  updateProgress('reading text', 50)
  const text = await file.text()
  return { text }
}

async function extractFromDOCX(
  file: File,
  updateProgress: ProgressUpdater
): Promise<ExtractionResult> {
  updateProgress('loading DOCX', 20)
  const arrayBuffer = await file.arrayBuffer()
  updateProgress('extracting content', 50)
  const result = await mammoth.extractRawText({ arrayBuffer })
  return { text: result.value }
}

async function extractFromCSV(
  file: File,
  updateProgress: ProgressUpdater
): Promise<ExtractionResult> {
  updateProgress('reading CSV', 20)
  const text = await file.text()
  updateProgress('parsing CSV', 60)
  const result = Papa.parse(text, { header: true })
  return {
    text: JSON.stringify(result.data, null, 2),
    metadata: {
      fields: result.meta.fields,
      rowCount: result.data.length
    }
  }
}

async function extractFromXLSX(
  file: File,
  updateProgress: ProgressUpdater
): Promise<ExtractionResult> {
  updateProgress('loading XLSX', 20)
  const arrayBuffer = await file.arrayBuffer()
  updateProgress('parsing XLSX', 50)
  const workbook = XLSX.read(arrayBuffer, { type: 'array' })
  let text = ''
  const metadata: Record<string, any> = {
    sheetNames: workbook.SheetNames,
    sheetCount: workbook.SheetNames.length
  }

  workbook.SheetNames.forEach((sheetName, index) => {
    const worksheet = workbook.Sheets[sheetName]
    const json = XLSX.utils.sheet_to_json(worksheet)
    text += `Sheet: ${sheetName}\n${JSON.stringify(json, null, 2)}\n\n`
    updateProgress('extracting sheets', 50 + (40 * (index + 1)) / workbook.SheetNames.length)
  })

  return { text, metadata }
}

export { extractTextFromFile, UnsupportedFileTypeError }
