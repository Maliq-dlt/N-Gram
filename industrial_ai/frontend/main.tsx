import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import { App } from './App';
import { studioViews } from './LiveViews';

const container = document.getElementById('root');
if (!container) throw new Error('Studio root is missing.');
// Render once before the typed media/auth controllers bind; video elements retain identity.
flushSync(() => createRoot(container).render(<App />));
Object.assign(window, { studioViews });
