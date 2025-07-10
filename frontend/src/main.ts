import { mount } from 'svelte'
import './app.css'
import App from './App.svelte'

const app = mount(App, {
  target: document.getElementById('app')!,
})

// --- WebSocket Connection ---
const socket = new WebSocket('ws://localhost:8765');

socket.addEventListener('open', (event) => {
  console.log('Connected to WebSocket server');
  socket.send('Hello from Svelte!');
});

socket.addEventListener('message', (event) => {
  console.log('Message from server ', event.data);
});

socket.addEventListener('close', (event) => {
  console.log('Disconnected from WebSocket server');
});

socket.addEventListener('error', (error) => {
  console.error('WebSocket error:', error);
});

export default app
