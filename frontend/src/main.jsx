import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

document.documentElement.dataset.env = import.meta.env.VITE_RHADIX_ENV || 'production'

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
