import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import { initializeColorScheme } from './utils/colorScheme';

// Áp dụng chế độ sáng/tối lên class <html> trước khi render, để không có
// "nháy" màu. Xem utils/colorScheme.ts để hiểu vì sao mặc định là sáng thay vì
// bám theo hệ điều hành.
initializeColorScheme();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
