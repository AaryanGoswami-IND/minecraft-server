const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// Minecraft server configuration
const SERVER_DIR = path.join(__dirname, '..');
const SERVER_JAR = 'server.jar';

let minecraftProcess = null;
let serverStatus = 'stopped';
let consoleHistory = [];
const MAX_HISTORY = 500;

// Get server properties
function getServerProperties() {
    try {
        const propsPath = path.join(SERVER_DIR, 'server.properties');
        const content = fs.readFileSync(propsPath, 'utf8');
        const props = {};
        content.split('\n').forEach(line => {
            if (line && !line.startsWith('#')) {
                const [key, ...valueParts] = line.split('=');
                if (key) props[key.trim()] = valueParts.join('=').trim();
            }
        });
        return props;
    } catch (err) {
        return {};
    }
}

// Socket.IO connection handling
io.on('connection', (socket) => {
    console.log('Client connected');

    // Send current status and history
    socket.emit('status', serverStatus);
    socket.emit('history', consoleHistory);
    socket.emit('properties', getServerProperties());

    // Start server command
    socket.on('start', () => {
        if (minecraftProcess) {
            socket.emit('console', '[Manager] Server is already running!');
            return;
        }

        serverStatus = 'starting';
        io.emit('status', serverStatus);
        io.emit('console', '[Manager] Starting Minecraft server...');

        minecraftProcess = spawn('java', [
            '-Xms1G',
            '-Xmx2G',
            '-XX:+UseG1GC',
            '-XX:+ParallelRefProcEnabled',
            '-XX:MaxGCPauseMillis=200',
            '-jar',
            SERVER_JAR,
            'nogui'
        ], {
            cwd: SERVER_DIR,
            stdio: ['pipe', 'pipe', 'pipe']
        });

        minecraftProcess.stdout.on('data', (data) => {
            const lines = data.toString().split('\n').filter(l => l.trim());
            lines.forEach(line => {
                consoleHistory.push(line);
                if (consoleHistory.length > MAX_HISTORY) consoleHistory.shift();
                io.emit('console', line);

                // Detect server ready
                if (line.includes('Done') && line.includes('For help')) {
                    serverStatus = 'running';
                    io.emit('status', serverStatus);
                }
            });
        });

        minecraftProcess.stderr.on('data', (data) => {
            const lines = data.toString().split('\n').filter(l => l.trim());
            lines.forEach(line => {
                consoleHistory.push(`[ERROR] ${line}`);
                if (consoleHistory.length > MAX_HISTORY) consoleHistory.shift();
                io.emit('console', `[ERROR] ${line}`);
            });
        });

        minecraftProcess.on('close', (code) => {
            io.emit('console', `[Manager] Server stopped with code ${code}`);
            serverStatus = 'stopped';
            io.emit('status', serverStatus);
            minecraftProcess = null;
        });

        minecraftProcess.on('error', (err) => {
            io.emit('console', `[Manager] Error: ${err.message}`);
            serverStatus = 'stopped';
            io.emit('status', serverStatus);
            minecraftProcess = null;
        });
    });

    // Stop server command
    socket.on('stop', () => {
        if (!minecraftProcess) {
            socket.emit('console', '[Manager] Server is not running!');
            return;
        }

        serverStatus = 'stopping';
        io.emit('status', serverStatus);
        io.emit('console', '[Manager] Stopping server...');

        minecraftProcess.stdin.write('stop\n');
    });

    // Send command to server
    socket.on('command', (cmd) => {
        if (!minecraftProcess) {
            socket.emit('console', '[Manager] Server is not running!');
            return;
        }

        io.emit('console', `> ${cmd}`);
        minecraftProcess.stdin.write(cmd + '\n');
    });

    // Restart server
    socket.on('restart', () => {
        if (minecraftProcess) {
            serverStatus = 'restarting';
            io.emit('status', serverStatus);
            io.emit('console', '[Manager] Restarting server...');

            minecraftProcess.stdin.write('stop\n');

            minecraftProcess.on('close', () => {
                setTimeout(() => {
                    socket.emit('start');
                }, 2000);
            });
        } else {
            socket.emit('start');
        }
    });

    socket.on('disconnect', () => {
        console.log('Client disconnected');
    });
});

// Start the manager server
const PORT = 3000;
server.listen(PORT, () => {
    console.log(`\n========================================`);
    console.log(`  Minecraft Server Manager`);
    console.log(`  Open: http://localhost:${PORT}`);
    console.log(`========================================\n`);
});
