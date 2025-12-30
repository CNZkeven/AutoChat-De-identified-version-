const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const requiredFiles = [
  'frontend/index.html',
  'frontend/login.html',
  'frontend/register.html',
  'frontend/course.html',
  'frontend/task.html',
  'frontend/ideological.html',
  'frontend/evaluation.html',
  'frontend/exploration.html',
  'frontend/competition.html',
  'frontend/style.css',
  'frontend/js/auth.js',
  'frontend/js/chat-common.js',
  'frontend/js/config.js',
  'frontend/js/course.js',
  'frontend/js/task.js',
  'frontend/js/ideological.js',
  'frontend/js/evaluation.js',
  'frontend/js/exploration.js',
  'frontend/js/competition.js',
  'frontend/js/login.js',
  'frontend/js/register.js'
];

const missing = requiredFiles.filter((file) => !fs.existsSync(path.join(root, file)));
if (missing.length > 0) {
  console.error('Missing frontend files:');
  missing.forEach((file) => console.error(` - ${file}`));
  process.exit(1);
}

console.log('Frontend file verification passed.');
