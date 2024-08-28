<template>
  <div class="spreadsheet-viewer">
    <div v-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="!data" class="loading-message">Loading spreadsheet...</div>
    <div v-else class="spreadsheet-content">
      <table>
        <thead>
          <tr>
            <th v-for="(header, index) in headers" :key="index">{{ header }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in data" :key="rowIndex">
            <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, watch } from 'vue'
import * as XLSX from 'xlsx'

export default defineComponent({
  name: 'SpreadsheetViewer',
  props: {
    contentUrl: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const data = ref<any[][]>([])
    const headers = ref<string[]>([])
    const error = ref<string | null>(null)

    const loadSpreadsheet = async (url: string) => {
      try {
        const response = await fetch(url)
        const arrayBuffer = await response.arrayBuffer()
        const workbook = XLSX.read(arrayBuffer, { type: 'array' })

        const firstSheetName = workbook.SheetNames[0]
        const worksheet = workbook.Sheets[firstSheetName]

        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 })

        if (jsonData.length > 0) {
          headers.value = jsonData[0] as string[]
          data.value = jsonData.slice(1) as any[][]
        }

        error.value = null
      } catch (err) {
        console.error('Error loading spreadsheet:', err)
        error.value = `Error loading spreadsheet: ${err instanceof Error ? err.message : String(err)}`
        data.value = []
        headers.value = []
      }
    }

    watch(
      () => props.contentUrl,
      (newUrl) => {
        if (newUrl) {
          loadSpreadsheet(newUrl)
        }
      },
      { immediate: true }
    )

    return { data, headers, error }
  }
})
</script>

<style scoped>
.spreadsheet-viewer {
  height: 100%;
  overflow: auto;
  padding: 1rem;
}

.spreadsheet-content {
  font-family: Arial, sans-serif;
  font-size: 14px;
}

table {
  border-collapse: collapse;
  width: 100%;
}

th,
td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

th {
  background-color: #f2f2f2;
  font-weight: bold;
}

tr:nth-child(even) {
  background-color: #f9f9f9;
}

.error-message,
.loading-message {
  color: #666;
  text-align: center;
  padding: 1rem;
}

.error-message {
  color: red;
}
</style>
