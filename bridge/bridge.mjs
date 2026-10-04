#!/usr/bin/env node
/**
 * PCSX2 Web Station Bridge portátil.
 * Requer Node.js 18+; não instala pacotes e não inclui BIOS/ISOs.
 */
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { spawn, execFile } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PCSX2_BRIDGE_PORT || 8765);
const TOKEN = process.env.PCSX2_BRIDGE_TOKEN || 'pcsx2-token';
const CONFIG = path.join(os.homedir(), '.pcsx2_launcher.json');
const CACHE = path.join(ROOT, '..', 'isos');
const EXTENSIONS = new Set(['.iso', '.chd', '.bin', '.cso', '.gz', '.mdf', '.img']);

async function load() {
  let data = {};
  try { data = JSON.parse(await fs.readFile(CONFIG, 'utf8')); } catch {}
  data.exe ??= await detectPcsx2();
  data.fullscreen ??= true;
  data.games ??= [];
  data.links ??= [];
  return data;
}

async function save(data) {
  await fs.writeFile(CONFIG, JSON.stringify(data, null, 2), 'utf8');
}

function commandExists(command) {
  return new Promise(resolve => execFile(process.platform === 'win32' ? 'where' : 'which', [command], { windowsHide: true }, error => resolve(!error)));
}

async function detectPcsx2() {
  if (process.platform === 'win32') {
    const roots = [process.env.ProgramFiles, process.env['ProgramFiles(x86)'], process.env.LOCALAPPDATA].filter(Boolean);
    const candidates = roots.flatMap(root => [
      path.join(root, 'PCSX2', 'pcsx2-qt.exe'),
      path.join(root, 'PCSX2', 'pcsx2.exe'),
      path.join(root, 'Programs', 'PCSX2', 'pcsx2-qt.exe')
    ]);
    return candidates.find(existsSync) || '';
  }
  if (process.platform === 'darwin') {
    const candidate = '/Applications/PCSX2.app/Contents/MacOS/PCSX2';
    if (existsSync(candidate)) return candidate;
  }
  if (await commandExists('flatpak')) {
    return 'flatpak:net.pcsx2.PCSX2';
  }
  for (const command of ['pcsx2-qt', 'pcsx2']) {
    if (await commandExists(command)) return command;
  }
  return '';
}

async function scanDirectory(folder) {
  const root = path.resolve(folder);
  const stat = await fs.stat(root).catch(() => null);
  if (!stat?.isDirectory()) throw new Error(`A pasta '${folder}' não é válida.`);
  const found = [];
  async function walk(dir) {
    for (const entry of await fs.readdir(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) await walk(full);
      else if (EXTENSIONS.has(path.extname(entry.name).toLowerCase())) found.push(full);
    }
  }
  await walk(root);
  const data = await load();
  const known = new Set(data.games.map(game => game.path));
  let added = 0;
  for (const file of found) {
    const resolved = path.resolve(file);
    if (known.has(resolved)) continue;
    data.games.push({ name: path.basename(resolved, path.extname(resolved)), path: resolved, added_at: Date.now(), last_played: null });
    known.add(resolved); added++;
  }
  await save(data);
  return { added, total: found.length };
}

function json(res, status, value) {
  const body = JSON.stringify(value);
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': Buffer.byteLength(body), 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'X-Token, Content-Type', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS' });
  res.end(body);
}

function authorized(req) { return req.headers['x-token'] === TOKEN || new URL(req.url, 'http://localhost').searchParams.get('token') === TOKEN; }
async function body(req) {
  let raw = ''; for await (const chunk of req) raw += chunk;
  return raw ? JSON.parse(raw) : {};
}

async function play(data, index) {
  const game = data.games[index];
  if (!game) throw new Error('Índice de jogo inválido.');
  if (!existsSync(game.path)) throw new Error(`Arquivo do jogo não encontrado: ${game.path}`);
  const exe = String(data.exe || '').trim();
  if (!exe) throw new Error('Configure o executável do PCSX2 na aba Bridge.');
  game.last_played = Date.now(); await save(data);
  const args = ['-batch', data.fullscreen ? '-fullscreen' : '-nofullscreen', '--', game.path];
  const child = exe.startsWith('flatpak:') ? spawn('flatpak', ['run', exe.slice(8), ...args], { detached: true, stdio: 'ignore' }) : spawn(exe, args, { detached: true, stdio: 'ignore', windowsHide: true });
  child.unref();
}

async function route(req, res) {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  if (req.method === 'OPTIONS') return json(res, 204, {});
  if (req.method === 'GET' && url.pathname === '/') {
    const html = `<!doctype html><meta charset="utf-8"><title>PCSX2 Bridge</title><style>body{font:16px system-ui;max-width:680px;margin:48px auto;padding:0 20px;background:#101522;color:#eef}code{background:#202a3d;padding:3px 6px;border-radius:4px}.ok{color:#58d68d}</style><h1>PCSX2 Web Station Bridge</h1><p class="ok">Bridge online</p><p>Conecte o site usando <code>http://127.0.0.1:${PORT}</code> e o token configurado.</p><p>O Bridge executa apenas o PCSX2 instalado localmente. BIOS e jogos devem ser fornecidos pelo usuário.</p>`;
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }); return res.end(html);
  }
  if (!authorized(req)) return json(res, 403, { error: 'Token inválido.' });
  if (req.method === 'GET' && url.pathname === '/health') return json(res, 200, { ok: true, bridge: 'node', version: '1.0.0' });
  if (req.method === 'GET' && url.pathname === '/api/state') return json(res, 200, await load());
  if (req.method !== 'POST') return json(res, 404, { error: 'Rota não encontrada.' });
  const input = await body(req);
  const data = await load();
  try {
    if (url.pathname === '/api/play') await play(data, Number(input.index));
    else if (url.pathname === '/api/settings') { if ('exe' in input) data.exe = String(input.exe).trim(); if ('fullscreen' in input) data.fullscreen = Boolean(input.fullscreen); await save(data); }
    else if (url.pathname === '/api/add') { const resolved = path.resolve(String(input.path || '').replace(/^"|"$/g, '')); if (!existsSync(resolved)) throw new Error('O arquivo não existe.'); data.games.push({ name: path.basename(resolved, path.extname(resolved)), path: resolved, added_at: Date.now(), last_played: null }); await save(data); }
    else if (url.pathname === '/api/scan') return json(res, 200, await scanDirectory(String(input.path || '')));
    else if (url.pathname === '/api/remove') { data.games.splice(Number(input.index), 1); await save(data); }
    else if (url.pathname === '/api/rename') { const game = data.games[Number(input.index)]; if (!game) throw new Error('Índice inválido.'); game.name = String(input.name || '').trim(); if (!game.name) throw new Error('O nome não pode ser vazio.'); await save(data); }
    else if (url.pathname === '/api/add_link') { const value = String(input.url || '').trim(); const parsed = new URL(value); if (!['http:', 'https:', 'magnet:'].includes(parsed.protocol) && !value.toLowerCase().endsWith('.torrent')) throw new Error('URL não suportada.'); data.links.push({ name: String(input.name || '').trim(), url: value, source: value.includes('drive.google.com') ? 'Google Drive' : (parsed.protocol === 'magnet:' || value.toLowerCase().endsWith('.torrent') ? 'Torrent' : 'Link'), added_at: Date.now() }); await save(data); }
    else if (url.pathname === '/api/remove_link') { data.links.splice(Number(input.index), 1); await save(data); }
    else if (url.pathname === '/api/drive') return json(res, 400, { error: 'O Bridge Node não baixa arquivos. Use um caminho local ou o download do Google Drive no aplicativo configurado.' });
    else return json(res, 404, { error: 'Rota não encontrada.' });
    return json(res, 200, { error: '' });
  } catch (error) { return json(res, 400, { error: error.message }); }
}

http.createServer((req, res) => route(req, res).catch(error => json(res, 500, { error: error.message }))).listen(PORT, '0.0.0.0', () => {
  console.log(`PCSX2 Web Station Bridge online em http://127.0.0.1:${PORT}`);
  console.log(`Token: ${TOKEN}`);
});
