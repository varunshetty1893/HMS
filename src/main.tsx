import {createRoot} from 'react-dom/client';
import './index.css';
import '../admin-web/src/index.css';
import App from './App.tsx';

createRoot(document.getElementById('root')!).render(<App />);
