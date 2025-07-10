<script lang="ts">
  import { onMount } from 'svelte';

  let lastMidiMessage = "Waiting for MIDI...";
  let deployLogs: string[] = [];
  let isDeploying = false;

  // Connection status indicators
  let backendConnected = false; // Main engine connection

  let mainSocket: WebSocket; // Main backend socket

  let midiFiles: string[] = []; // To store the list of MIDI files
  let selectedMidiFile: string = ""; // The currently selected MIDI file
  let midiTriggerNote: number = 48; // Default trigger note for MIDI playback (C2)
  let loadedMidiStatus: string = "No MIDI file loaded.";

  // New state for backend selection
  let backendTarget: 'pi' | 'mac' = 'pi'; // Default to Pi
  const pi_ip_address = "192.168.1.142"; // Your Pi's IP
  const mac_ip_address = "localhost"; // Your Mac's localhost

  const mainBackendPort = 8765;

  function getMainBackendSocketUrl(): string {
    const ip = backendTarget === 'pi' ? pi_ip_address : mac_ip_address;
    return `ws://${ip}:${mainBackendPort}`;
  }

  function connectMainBackend() {
    if (mainSocket) {
      mainSocket.close();
    }

    const socket_url = getMainBackendSocketUrl();
    console.log(`Connecting to Main Backend at ${socket_url}`);
    mainSocket = new WebSocket(socket_url);

    mainSocket.addEventListener('open', () => {
      backendConnected = true;
      lastMidiMessage = `Connected to backend (${backendTarget}).`;
      requestMidiFiles(); // Request MIDI files on connection
    });

    mainSocket.addEventListener('message', (event) => {
      const message = event.data;
      try {
        const parsed = JSON.parse(message);
        
        // Handle structured JSON messages from backend
        if (parsed.type === 'midi_file_list') {
          midiFiles = parsed.files;
          if (midiFiles.length > 0 && !selectedMidiFile) {
            selectedMidiFile = midiFiles[0]; // Select the first file by default
          }
        } else {
          // Handle other JSON messages if needed
          console.log("Received unknown JSON message from main backend:", parsed);
        }
      } catch (e) {
        // Handle non-JSON messages (like simple MIDI messages)
        if (message.startsWith('MIDI_LOADED:')) {
          loadedMidiStatus = `Loaded: ${message.substring('MIDI_LOADED:'.length).trim()}`;
        } else if (message.startsWith('MIDI_ERROR:')) {
          loadedMidiStatus = `Error: ${message.substring('MIDI_ERROR:'.length).trim()}`;
        } else if (message.startsWith('DEPLOY_LOG_START')) {
          deployLogs = ["Starting full refresh..."];
        } else if (message.startsWith('DEPLOY_LOG_END')) {
          // Deployment finished, check logs for success/failure
          isDeploying = false;
          if (deployLogs.some(log => log.startsWith('FAILED:'))) {
            deployLogs = [...deployLogs, "FAILED: Deployment failed."];
          } else {
            deployLogs = [...deployLogs, "SUCCESS: Deployment completed."];
          }
        } else if (message.startsWith('DEPLOY_OUTPUT:')) {
          deployLogs = [...deployLogs, message.substring('DEPLOY_OUTPUT:'.length).trim()];
        } else if (message.startsWith('DEPLOY_ERROR:')) {
          deployLogs = [...deployLogs, `ERROR: ${message.substring('DEPLOY_ERROR:'.length).trim()}`];
        } else if (message.startsWith('DEPLOY_SUCCESS:')) {
          deployLogs = [...deployLogs, message.substring('DEPLOY_SUCCESS:'.length).trim()];
          isDeploying = false;
        } else if (message.startsWith('DEPLOY_FAILED:')) {
          deployLogs = [...deployLogs, message.substring('DEPLOY_FAILED:'.length).trim()];
          isDeploying = false;
        } else {
          lastMidiMessage = message;
        }
      }
    });

    mainSocket.addEventListener('close', () => {
      backendConnected = false;
      lastMidiMessage = "Connection to main backend lost.";
    });

    mainSocket.addEventListener('error', () => {
      backendConnected = false;
      lastMidiMessage = "Error connecting to main backend.";
    });
  }

  function handleDeploy() {
    if (mainSocket && mainSocket.readyState === WebSocket.OPEN) {
      deployLogs = []; // Clear previous logs
      isDeploying = true;
      mainSocket.send(JSON.stringify({ command: 'deploy' })); // Send JSON command to main backend
    } else {
      deployLogs = ["ERROR: Main backend not connected for deployment."];
    }
  }

  function handleLoadMidi() {
    if (mainSocket && mainSocket.readyState === WebSocket.OPEN && selectedMidiFile) {
      mainSocket.send(JSON.stringify({
        command: 'load_midi',
        filename: selectedMidiFile,
        trigger_note: midiTriggerNote
      }));
      loadedMidiStatus = `Attempting to load ${selectedMidiFile} (Trigger: ${midiTriggerNote})...`;
    }
  }

  function requestMidiFiles() {
    if (mainSocket && mainSocket.readyState === WebSocket.OPEN) {
      mainSocket.send(JSON.stringify({ command: 'list_midi_files' }));
    }
  }

  // Initial connections on mount
  onMount(() => {
    connectMainBackend();

    // Cleanup the connections when the component is destroyed
    return () => {
      if (mainSocket) {
        mainSocket.close();
      }
    };
  });

  // Reconnect when backendTarget changes
  $: if (backendTarget) {
    connectMainBackend();
  }

</script>

<main>
  <h1>RexLoop Controller - Test 1</h1>
  
  <div class="connection-status-indicators">
    <div class="status-light" class:connected={backendConnected}></div>
    <span>Main Backend</span>
  </div>

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
          <p class={log.startsWith('ERROR:') || log.startsWith('FAILED:') ? 'log-error' : ''}>{log}</p>
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

  .connection-status-indicators {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-top: 1em;
    gap: 10px;
  }

  .status-light {
    width: 15px;
    height: 15px;
    border-radius: 50%;
    background-color: #888; /* Grey for disconnected */
    border: 1px solid #555;
  }

  .status-light.connected {
    background-color: #00ff00; /* Green for connected */
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