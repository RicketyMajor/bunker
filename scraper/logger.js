const fs = require('fs');
const util = require('util');
const path = require('path');

const logDir = path.join(__dirname, 'logs');
if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
}

function getLogFile() {
    const date = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
    return path.join(logDir, `scraper_${date}.log`);
}

function writeLog(level, args) {
    const msg = util.format.apply(null, args);
    const timestamp = new Date().toISOString();
    const formattedMsg = `[${timestamp}] [${level}] ${msg}\n`;
    fs.appendFileSync(getLogFile(), formattedMsg);
}

const originalLog = console.log;
const originalError = console.error;
const originalWarn = console.warn;
const originalInfo = console.info;

console.log = function () {
    writeLog('INFO', arguments);
    originalLog.apply(console, arguments);
};

console.error = function () {
    writeLog('ERROR', arguments);
    originalError.apply(console, arguments);
};

console.warn = function () {
    writeLog('WARN', arguments);
    originalWarn.apply(console, arguments);
};

console.info = function () {
    writeLog('INFO', arguments);
    originalInfo.apply(console, arguments);
};
