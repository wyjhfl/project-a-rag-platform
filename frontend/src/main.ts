import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'

import App from './App.vue'
import { installElementPlus } from './plugins/element-plus'

const app = createApp(App)
app.use(createPinia())
installElementPlus(app)
app.mount('#app')
