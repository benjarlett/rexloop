<script lang="ts">
  import { onMount } from 'svelte';

  let lastMidiMessage = "Waiting for MIDI...";
  let deployLogs: string[] = [];
  let isDeploying = false;
  let socket: WebSocket;

  let midiFiles: string[] = []; // To store the list of MIDI files
  let selectedMidiFile: string = ""; // The currently selected MIDI file
  let midiTriggerNote: number = 48; // Default trigger note for MIDI playback (C2)
  let loadedMidiStatus: string = "No MIDI file loaded.";

  // New state for backend selection
  let backendTarget: 'pi' | 'mac' = 'pi'; // Default to Pi
  const pi_ip_address = "192.168.1.142"; // Your Pi's IP
  const mac_ip_address = "localhost"; // Your Mac's localhost

  function getSocketUrl(): string {
    const ip = backendTarget === 'pi' ? pi_ip_address : mac_ip_address;
    return `ws://${ip}:8765`;
  }

  function connectWebSocket() {
    if (socket) {
      socket.close(); // Close existing connection if any
    }

    const socket_url = getSocketUrl();
    console.log(`Connecting to WebSocket at ${socket_url}`);
    socket = new WebSocket(socket_url);

    socket.addEventListener('open', () => {
      lastMidiMessage = `Connected to backend (${backendTarget}).`;
      requestMidiFiles(); // Request MIDI files on connection
    });

    socket.addEventListener('message', (event) => {
      const message = event.data;
      try {
        const parsed = JSON.parse(message);
        if (parsed.type === 'midi_file_list') {
          midiFiles = parsed.files;
          if (midiFiles.length > 0 && !selectedMidiFile) {
            selectedMidiFile = midiFiles[0]; // Select the first file by default
          }
        } else {
          // Handle other JSON messages if needed
          console.log("Received JSON message:", parsed);
        }
      } catch (e) {
        // Handle non-JSON messages (like simple MIDI messages or deploy logs)
        if (message.startsWith('DEPLOY_START')) {
          isDeploying = true;
          deployLogs = [message];
        } else if (message.startsWith('DEPLOY_LOG') || message.startsWith('DEPLOY_ERROR')) {
          deployLogs = [...deployLogs, message];
        } else if (message.startsWith('DEPLOY_END')) {
          isDeploying = false;
          deployLogs = [...deployLogs, message];
        } else if (message.startsWith('MIDI_LOADED:')) {
          loadedMidiStatus = `Loaded: ${message.substring('MIDI_LOADED:'.length).trim()}`;
        } else if (message.startsWith('MIDI_ERROR:')) {
          loadedMidiStatus = `Error: ${message.substring('MIDI_ERROR:'.length).trim()}`;
        } else {
          lastMidiMessage = message;
        }
      }
    });

    socket.addEventListener('close', () => {
      lastMidiMessage = "Connection lost.";
    });

    socket.addEventListener('error', () => {
      lastMidiMessage = "Error connecting.";
    });
  }

  function handleDeploy() {
    if (socket && socket.readyState === WebSocket.OPEN) {
      deployLogs = []; // Clear previous logs
      isDeploying = true;
      socket.send(JSON.stringify({ command: 'deploy' })); // Send JSON command
    }
  }

  function handleLoadMidi() {
    if (socket && socket.readyState === WebSocket.OPEN && selectedMidiFile) {
      socket.send(JSON.stringify({
        command: 'load_midi',
        filename: selectedMidiFile,
        trigger_note: midiTriggerNote
      }));
      loadedMidiStatus = `Attempting to load ${selectedMidiFile} (Trigger: ${midiTriggerNote})...`;
    }
  }

  function requestMidiFiles() {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ command: 'list_midi_files' }));
    }
  }

  // Initial connection on mount
  onMount(() => {
    connectWebSocket();

    // Cleanup the connection when the component is destroyed
    return () => {
      if (socket) {
        socket.close();
      }
    };
  });

  // Reconnect when backendTarget changes
  $: if (backendTarget) {
    connectWebSocket();
  }

</script>

<main>
  <h1>RexLoop Controller</h1>
  
  <div class="connection-target-select">
    <label for="backend-target">Connect to Backend:</label>
    <select id="backend-target" bind:value={backendTarget}>
      <option value="pi">Raspberry Pi ({pi_ip_address})</option>
      <option value="mac">Mac (localhost)</option>
    </select>
  </div>

  <div class="status-box">
    <p>{lastMidiMessage}</p>
  </div>

  <div class="midi-load-section">
    <h2>MIDI Loop Channel 1</h2>
    <div class="input-group">
      <label for="midi-file-select">Select MIDI File:</label>
      <select id="midi-file-select" bind:value={selectedMidiFile}>
        {#each midiFiles as file}
          <option value={file}>{file}</option>
        {/each}
      </select>
    </div>
    <div class="input-group">
      <label for="trigger-note">Trigger Note (0-127):</label>
      <input type="number" id="trigger-note" bind:value={midiTriggerNote} min="0" max="127" />
    </div>
    <button on:click={handleLoadMidi}>Load MIDI Loop</button>
    <p class="midi-status">{loadedMidiStatus}</p>
  </div>

  <div class="deploy-section">
    <button on:click={handleDeploy} disabled={isDeploying || backendTarget === 'mac'}>
      {isDeploying ? 'Deploying...' : 'Deploy Latest Code'}
    </button>
    {#if backendTarget === 'mac'}
      <p class="deploy-warning">Deployment is only available when connected to Raspberry Pi.</p>
    {/if}
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
  :root {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
    background-color: #222;
    color: #eee;
  }

  main {
    text-align: center;
    padding: 2em;
  }

  h1 {
    color: #ff3e00;
  }

  .connection-target-select {
    margin-bottom: 1em;
  }

  .connection-target-select label {
    margin-right: 10px;
  }

  .connection-target-select select {
    padding: 5px;
    border-radius: 4px;
    border: 1px solid #555;
    background-color: #333;
    color: #eee;
  }

  .status-box {
    background-color: #333;
    border: 1px solid #555;
    border-radius: 8px;
    padding: 20px;
    margin-top: 2em;
    min-height: 50px;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .deploy-section, .midi-load-section {
    margin-top: 2em;
    padding: 1em;
    border: 1px solid #444;
    border-radius: 8px;
    background-color: #2a2a2a;
  }

  .midi-load-section h2 {
    color: #00ff99;
    margin-top: 0;
  }

  .input-group {
    margin-bottom: 1em;
  }

  .input-group label {
    display: block;
    margin-bottom: 0.5em;
    font-weight: bold;
  }

  .midi-load-section input[type="text"],
  .midi-load-section input[type="number"],
  .midi-load-section select {
    padding: 8px;
    border-radius: 4px;
    border: 1px solid #555;
    background-color: #333;
    color: #eee;
    margin-right: 10px;
    width: 200px;
  }

  .midi-load-section button {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 8px 15px;
    border-radius: 5px;
    cursor: pointer;
    transition: background-color 0.3s;
  }

  .midi-load-section button:hover {
    background-color: #0056b3;
  }

  .midi-status {
    margin-top: 1em;
    font-style: italic;
    color: #bbb;
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