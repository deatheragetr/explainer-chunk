import '@fortawesome/fontawesome-free/css/all.css'
import 'prismjs/themes/prism-tomorrow.css'
import 'prismjs/plugins/line-numbers/prism-line-numbers.css'
import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import store from './store/auth'
import './index.css' // This file will include Tailwind
import 'pdfjs-dist/web/pdf_viewer.css'
import Toast from 'vue-toastification'
import 'vue-toastification/dist/index.css'
import '@fortawesome/fontawesome-free/css/all.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(store)
app.use(Toast)

app.mount('#app')
