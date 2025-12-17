// Connect to Socket.IO server
const socket = io();

// DOM Elements
const consoleEl = document.getElementById('console');
const commandInput = document.getElementById('commandInput');
const sendCmdBtn = document.getElementById('sendCmd');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const restartBtn = document.getElementById('restartBtn');
const clearConsoleBtn = document.getElementById('clearConsole');
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const propertiesGrid = document.getElementById('propertiesGrid');

// Navigation
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const tab = item.dataset.tab;

        // Update nav
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');

        // Update content
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.getElementById(`${tab}-tab`).classList.add('active');
    });
});

// Server Control
startBtn.addEventListener('click', () => socket.emit('start'));
stopBtn.addEventListener('click', () => socket.emit('stop'));
restartBtn.addEventListener('click', () => socket.emit('restart'));

// Send Command
function sendCommand() {
    const cmd = commandInput.value.trim();
    if (cmd) {
        socket.emit('command', cmd);
        commandInput.value = '';
    }
}

sendCmdBtn.addEventListener('click', sendCommand);
commandInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendCommand();
});

// Clear Console
clearConsoleBtn.addEventListener('click', () => {
    consoleEl.innerHTML = '';
});

// Socket Events
socket.on('status', (status) => {
    statusIndicator.className = 'status-indicator ' + status;
    statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);

    // Update button states
    startBtn.disabled = status === 'running' || status === 'starting';
    stopBtn.disabled = status === 'stopped' || status === 'stopping';
});

socket.on('console', (line) => {
    appendConsoleLine(line);
});

socket.on('history', (lines) => {
    lines.forEach(line => appendConsoleLine(line));
});

socket.on('properties', (props) => {
    propertiesGrid.innerHTML = '';

    const importantProps = ['motd', 'max-players', 'difficulty', 'gamemode', 'level-name', 'online-mode', 'view-distance', 'server-port'];

    importantProps.forEach(key => {
        if (props[key] !== undefined) {
            const item = document.createElement('div');
            item.className = 'property-item';
            item.innerHTML = `
                <span class="property-key">${key}</span>
                <span class="property-value">${props[key]}</span>
            `;
            propertiesGrid.appendChild(item);
        }
    });
});

// Helper Functions
function appendConsoleLine(text) {
    const line = document.createElement('div');
    line.className = 'console-line';

    // Color coding
    if (text.includes('[Manager]')) {
        line.classList.add('info');
    } else if (text.includes('ERROR') || text.includes('Exception')) {
        line.classList.add('error');
    } else if (text.includes('WARN')) {
        line.classList.add('warn');
    } else if (text.includes('Done!') || text.includes('joined')) {
        line.classList.add('success');
    } else if (text.startsWith('>')) {
        line.classList.add('command');
    }

    // Timestamp
    const now = new Date();
    const time = now.toTimeString().split(' ')[0];
    line.textContent = `[${time}] ${text}`;

    consoleEl.appendChild(line);
    consoleEl.scrollTop = consoleEl.scrollHeight;
}

// Initial message
appendConsoleLine('[Manager] Connected to Minecraft Server Manager');
appendConsoleLine('[Manager] Click "Start" to launch the server');
