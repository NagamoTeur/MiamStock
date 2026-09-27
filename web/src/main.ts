import { mount } from 'svelte';
import App from './App.svelte';
import './app.css';

const target = document.getElementById('app');
if (!target) throw new Error('#app introuvable');

const app = mount(App, { target });

// Le service worker n'est enregistré qu'en production : en dev, il servirait un
// bundle figé et masquerait les modifications en cours.
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    void navigator.serviceWorker.register('/sw.js');
  });
}

export default app;
