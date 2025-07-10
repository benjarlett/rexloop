<script lang="ts">
  import { onMount } from 'svelte';

  let lastMidiMessage = "Waiting for MIDI...";
  let deployLogs: string[] = [];
  let isDeploying = false;
  let socket: WebSocket;

  function handleDeploy() {
    if (socket && socket.readyState === WebSocket.OPEN) {
      deployLogs = []; // Clear previous logs
      isDeploying = true;
      socket.send('deploy');
    }
  }

  onMount(() => {
    const pi_ip_address = "192.168.1.100"; // <-- IMPORTANT: CHANGE THIS
    const socket_url = `ws://${pi_ip_address}:8765`;

    socket = new WebSocket(socket_url);

    socket.addEventListener('open', () => {
      lastMidiMessage = "Connected to backend.";
    });

    socket.addEventListener('message', (event) => {
      const message = event.data;
      if (message.startsWith('DEPLOY_START')) {
        isDeploying = true;
        deployLogs = [message];
      } else if (message.startsWith('DEPLOY_LOG') || message.startsWith('DEPLOY_ERROR')) {
        deployLogs = [...deployLogs, message];
      } else if (message.startsWith('DEPLOY_END')) {
        isDeploying = false;
        deployLogs = [...deployLogs, message];
      } else {
        lastMidiMessage = message;
      }
    });

    socket.addEventListener('close', () => {
      lastMidiMessage = "Connection lost.";
    });

    socket.addEventListener('error', () => {
      lastMidiMessage = "Error connecting.";
    });

    return () => socket?.close();
  });

</script>

<main>
  <h1>RexLoop Controller</h1>
  
  <div class="status-box">
    <p>{lastMidiMessage}</p>
  </div>

  <div class="deploy-section">
    <button on:click={handleDeploy} disabled={isDeploying}>
      {isDeploying ? 'Deploying...' : 'Deploy Latest Code'}
    </button>
    {#if deployLogs.length > 0}
      <div class="log-box">
        {#each deployLogs as log}
          <p class={log.startsWith('DEPLOY_ERROR') ? 'log-error' : ''}>{log}</p>
        {/each}
      </div>
    {/if}
  </div>
</main>

<style>
  /* ... existing styles ... */
  .deploy-section {
    margin-top: 2em;
  }
  button {
    background-color: #ff3e00;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 1em;
    transition: background-color 0.3s;
  }
  button:disabled {
    background-color: #555;
    cursor: not-allowed;
  }
  .log-box {
    background-color: #111;
    border: 1px solid #444;
    border-radius: 5px;
    padding: 10px;
    margin-top: 1em;
    text-align: left;
    max-height: 300px;
    overflow-y: auto;
  }
  .log-box p {
    font-family: monospace;
    font-size: 0.9em;
    white-space: pre-wrap;
    margin: 2px 0;
    color: #ccc;
  }
  .log-error {
    color: #ff4444 !important;
  }
</style>
