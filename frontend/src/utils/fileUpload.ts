import type { Ref } from 'vue'
import axios, { type AxiosResponse } from 'axios'
import { parallelLimit } from '@/utils/parallelLimit'
import type { ImportProgress, ExtractionResult } from '@/types'
import { extractTextFromFile } from '@/utils/textExtract'
import { createProgressUpdater } from '@/utils/progressUpdater'
import api from '@/api/axios'

const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB chunks, minimum chunk size S3 allows
const MAX_RETRIES = 3
const RETRY_DELAY = 1000 // 1 second

interface MultipartUploadInitResponse {
  uploadId: string
  fileKey: string
}

interface PresignedUrlResponse {
  presignedUrl: string
}

interface PartUploadResult {
  ETag: string
  PartNumber: number
}

interface uploadLargeFileResponse {
  id: string
  file_name: string
  file_type: string
  url_friendly_file_name: string
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function retryOperation<T>(
  operation: () => Promise<T>,
  retries: number = MAX_RETRIES
): Promise<T> {
  for (let i = 0; i < retries; i++) {
    try {
      return await operation()
    } catch (error) {
      console.error('Encountered error ', error)
      if (i === retries - 1) throw error
      console.log(`Attempt ${i + 1} failed, retrying...`)
      await sleep(RETRY_DELAY)
    }
  }
  throw new Error('Operation failed after max retries')
}

async function initiateMultipartUpload(
  file_name: string,
  fileType: string
): Promise<MultipartUploadInitResponse> {
  const response: AxiosResponse = await axios.post('http://localhost:8000/multipart-upload/', {
    file_name,
    file_type: fileType
  })

  return {
    uploadId: response.data.upload_id,
    fileKey: response.data.file_key
  }
}

async function uploadPart(url: string, part: Blob, partNumber: number): Promise<PartUploadResult> {
  console.log('url', url)
  console.log('part', part)
  console.log('partNumber', partNumber)
  const response: AxiosResponse = await axios.put(url, part, {
    headers: { 'Content-Type': 'application/octet-stream' },
    timeout: 30000 // 30 seconds
  })
  const ETag = response.headers.etag
  return { ETag, PartNumber: partNumber }
}

async function completeMultipartUpload(
  uploadId: string,
  fileKey: string,
  parts: PartUploadResult[]
): Promise<void> {
  await axios.put(`http://localhost:8000/multipart-upload/${uploadId}`, {
    file_key: fileKey,
    parts
  })
}

async function generatePresignedUrl(
  uploadId: string,
  fileKey: string,
  partNumber: number
): Promise<PresignedUrlResponse> {
  const response: AxiosResponse = await axios.post('http://localhost:8000/upload-url/', {
    upload_id: uploadId,
    file_key: fileKey,
    part_number: partNumber
  })
  return { presignedUrl: response.data.presigned_url }
}

export async function uploadLargeFile(
  file: File,
  fileType: string,
  importProgress: Ref<ImportProgress | null>,
  concurrency: number = 4
): Promise<uploadLargeFileResponse> {
  const updateProgress = createProgressUpdater(importProgress)

  const { uploadId, fileKey } = await initiateMultipartUpload(file.name, fileType)

  // const parts: PartUploadResult[] = []
  const chunks: { start: number; end: number; partNumber: number }[] = []
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE)

  console.log('totalChunks', totalChunks)
  console.log('file.size', file.size)

  updateProgress('preparing for upload', 10)

  for (let i = 0; i < totalChunks; i++) {
    const start = i * CHUNK_SIZE
    const end = Math.min(start + CHUNK_SIZE, file.size)
    updateProgress('preparing for upload', 10 + Math.floor(i / totalChunks) * 10)
    chunks.push({ start, end, partNumber: i + 1 })
  }

  updateProgress('uploading', 20)

  let chunksProcessed = 0
  const parts = await parallelLimit(chunks, concurrency, async (chunk) => {
    const { start, end, partNumber } = chunk
    const chunkData = file.slice(start, end)

    const { presignedUrl } = await generatePresignedUrl(uploadId, fileKey, partNumber)
    const partData = await retryOperation(() => uploadPart(presignedUrl, chunkData, partNumber))

    chunksProcessed++
    updateProgress('uploading', 20 + Math.floor((chunksProcessed / totalChunks) * 30))
    console.log(`Uploaded part ${partNumber} of ${totalChunks}`)
    return partData
  })

  updateProgress('completing upload', 55)

  await completeMultipartUpload(uploadId, fileKey, parts)

  const result: ExtractionResult = await extractTextFromFile(file, fileType, importProgress)
  console.log('Metadata:', result.metadata)

  updateProgress('finalizing', 70)

  const results = await api.post('/document-uploads/', {
    file_name: file.name,
    file_type: fileType,
    file_key: fileKey,
    extracted_text: result.text,
    extracted_metadata: result.metadata || {}
  })

  updateProgress('completed', 100)
  console.log('Upload completed successfully')
  return results.data
}
