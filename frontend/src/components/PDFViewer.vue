<template>
    <div class="pdf-viewer">
      <div v-if="loading" class="loading">Loading PDF...</div>
      <canvas ref="pdfCanvas"></canvas>
      <div class="controls">
        <button @click="prevPage" :disabled="currentPage === 1">Previous</button>
        <span>Page {{ currentPage }} of {{ totalPages }}</span>
        <button @click="nextPage" :disabled="currentPage === totalPages">Next</button>
      </div>
    </div>
  </template>
  
  <script lang="ts">
  import { defineComponent, ref, onMounted, watch } from 'vue';
  import * as pdfjsLib from 'pdfjs-dist/webpack.mjs';

  import PDFWorker from 'pdfjs-dist/build/pdf.worker.mjs?worker';
  pdfjsLib.GlobalWorkerOptions.workerPort = new PDFWorker();

  export default defineComponent({
    name: 'PDFViewer',
    props: {
      pdfUrl: {
        type: String,
        required: true
      }
    },
    setup(props) {
      const pdfCanvas = ref<HTMLCanvasElement | null>(null);
      const loading = ref(true);
      const currentPage = ref(1);
      const totalPages = ref(0);
      let pdfDoc: any = null;
  
      const renderPage = async (pageNum: number) => {
        if (!pdfDoc) return;
        
        const page = await pdfDoc.getPage(pageNum);
        const scale = 1.5;
        const viewport = page.getViewport({ scale });
  
        if (pdfCanvas.value) {
          const context = pdfCanvas.value.getContext('2d');
          pdfCanvas.value.height = viewport.height;
          pdfCanvas.value.width = viewport.width;
  
          const renderContext = {
            canvasContext: context!,
            viewport: viewport
          };
  
          await page.render(renderContext);
        }
      };
  
      const loadPDF = async () => {
        try {
          loading.value = true;
          console.log('Loading PDF from URL:', props.pdfUrl);
          pdfDoc = await pdfjsLib.getDocument(props.pdfUrl).promise;
          console.log('PDF loaded successfully. Number of pages:', pdfDoc.numPages);
          totalPages.value = pdfDoc.numPages;
          currentPage.value = 1;
          await renderPage(currentPage.value);
        } catch (error) {
            console.error('Error loading PDF:', error);
            if (error instanceof Error) {
            console.error('Error name:', error.name);
            console.error('Error message:', error.message);
            console.error('Error stack:', error.stack);
          }
            // You might want to set an error state here to display to the user
        } finally {
          loading.value = false;
        }
      };
  
      const prevPage = () => {
        if (currentPage.value > 1) {
          currentPage.value--;
          renderPage(currentPage.value);
        }
      };
  
      const nextPage = () => {
        if (currentPage.value < totalPages.value) {
          currentPage.value++;
          renderPage(currentPage.value);
        }
      };
  
      onMounted(() => {
        loadPDF();
      });
  
      watch(() => props.pdfUrl, () => {
        loadPDF();
      });
  
      return {
        pdfCanvas,
        loading,
        currentPage,
        totalPages,
        prevPage,
        nextPage
      };
    }
  });
  </script>
  
  <style scoped>
  .pdf-viewer {
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  
  .controls {
    margin-top: 1rem;
    display: flex;
    gap: 1rem;
    align-items: center;
  }
  
  canvas {
    max-width: 100%;
    height: auto;
  }
  
  .loading {
    font-size: 1.2rem;
    color: #666;
  }
  </style>