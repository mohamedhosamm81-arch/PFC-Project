const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || '0.0.0.0';
const API_KEY = process.env.PFC_API_KEY || '';
const DATA_FILE = process.env.PFC_DATA_FILE || path.join(__dirname, 'data', 'state.json');
const PUBLIC_DIR = __dirname;
const MAX_BODY = 5 * 1024 * 1024;

const resources = {
  users: 'users',
  patients: 'patients',
  organizations: 'organizations',
  rooms: 'rooms',
  sessions: 'sessions',
  actions: 'actions',
  notifications: 'notifications',
  routing: 'routing'
};

function send(res, status, body, headers = {}) {
  const payload = typeof body === 'string' ? body : JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': typeof body === 'string' ? 'text/plain; charset=utf-8' : 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': process.env.CORS_ORIGIN || '*',
    'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, Authorization',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
    ...headers
  });
  res.end(payload);
}

function readState() {
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
  } catch {
    return { version: 3, organizations: [], users: [], patients: [], rooms: [], sessions: [], actions: [], notifications: [], routing: {}, nextCode: 1 };
  }
}

function writeState(state) {
  fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true });
  const tmp = `${DATA_FILE}.${process.pid}.${crypto.randomBytes(4).toString('hex')}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(state, null, 2));
  fs.renameSync(tmp, DATA_FILE);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', chunk => {
      raw += chunk;
      if (raw.length > MAX_BODY) reject(new Error('Payload too large'));
    });
    req.on('end', () => {
      if (!raw) return resolve({});
      try { resolve(JSON.parse(raw)); } catch { reject(new Error('Request body must be valid JSON')); }
    });
    req.on('error', reject);
  });
}

function authorized(req, url) {
  if (!API_KEY || url.pathname === '/api/health') return true;
  const supplied = req.headers['x-api-key'] || String(req.headers.authorization || '').replace(/^Bearer\s+/i, '');
  return supplied && crypto.timingSafeEqual(Buffer.from(String(supplied)), Buffer.from(String(API_KEY)));
}

function scrubUser(user) {
  if (!user || process.env.EXPOSE_PASSWORDS === 'true') return user;
  const { password, ...safe } = user;
  return safe;
}

function scrubState(state) {
  return { ...state, users: (state.users || []).map(scrubUser), currentUser: null };
}

function match(record, query) {
  return Object.entries(query).every(([key, value]) => String(record?.[key] ?? '').toLowerCase() === String(value).toLowerCase());
}

async function handle(req, res) {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  if (req.method === 'OPTIONS') return send(res, 204, '');
  if (!authorized(req, url)) return send(res, 401, { error: 'Unauthorized', message: 'Provide a valid X-API-Key or Bearer token.' });
  if (url.pathname === '/api/health' && req.method === 'GET') return send(res, 200, { ok: true, service: 'pfc-api', timestamp: new Date().toISOString() });

  const state = readState();
  if (url.pathname === '/api/state' && req.method === 'GET') return send(res, 200, scrubState(state));
  if (url.pathname === '/api/state' && ['PUT', 'PATCH'].includes(req.method)) {
    const body = await readBody(req);
    writeState({ ...state, ...body, version: 3, updatedAt: new Date().toISOString() });
    return send(res, 200, { ok: true, state: scrubState(readState()) });
  }

  const matchPath = url.pathname.match(/^\/api\/([^/]+)(?:\/([^/]+))?$/);
  if (!matchPath || !resources[matchPath[1]]) return send(res, 404, { error: 'NotFound', message: 'Use /api/state or /api/{resource}[/{id}]' });
  const resource = resources[matchPath[1]];
  const id = matchPath[2];
  const query = Object.fromEntries(url.searchParams.entries());
  let collection = Array.isArray(state[resource]) ? state[resource] : [];
  if (resource === 'routing' && !Array.isArray(state[resource])) collection = [];

  if (req.method === 'GET') {
    const result = id ? collection.find(item => String(item.id ?? item.code) === String(id)) : collection.filter(item => match(item, query));
    if (id && !result) return send(res, 404, { error: 'NotFound' });
    return send(res, 200, id ? result : { data: result, count: result.length });
  }

  const body = await readBody(req);
  if (req.method === 'POST') {
    const item = { ...body };
    if (!item.id && resource !== 'patients') item.id = `${resource.slice(0, 3).toUpperCase()}-${crypto.randomBytes(4).toString('hex')}`;
    if (resource === 'patients' && item.code == null) item.code = state.nextCode || 1;
    collection.push(item);
    state[resource] = collection;
    if (resource === 'patients') state.nextCode = Number(item.code) + 1;
    writeState({ ...state, updatedAt: new Date().toISOString() });
    return send(res, 201, item);
  }

  if (!id) return send(res, 400, { error: 'BadRequest', message: 'An id or code is required for update/delete.' });
  const index = collection.findIndex(item => String(item.id ?? item.code) === String(id));
  if (index < 0) return send(res, 404, { error: 'NotFound' });
  if (req.method === 'DELETE') {
    const [removed] = collection.splice(index, 1);
    state[resource] = collection;
    writeState({ ...state, updatedAt: new Date().toISOString() });
    return send(res, 200, { ok: true, deleted: removed });
  }
  if (['PUT', 'PATCH'].includes(req.method)) {
    collection[index] = req.method === 'PUT' ? body : { ...collection[index], ...body };
    state[resource] = collection;
    writeState({ ...state, updatedAt: new Date().toISOString() });
    return send(res, 200, collection[index]);
  }
  return send(res, 405, { error: 'MethodNotAllowed' });
}

const server = http.createServer((req, res) => {
  if (req.url.startsWith('/api/')) {
    handle(req, res).catch(error => send(res, 400, { error: 'RequestError', message: error.message }));
    return;
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') return send(res, 405, { error: 'MethodNotAllowed' });
  const requested = decodeURIComponent(new URL(req.url, `http://${req.headers.host || 'localhost'}`).pathname);
  const file = requested === '/' ? 'index.html' : requested.replace(/^\//, '');
  const filePath = path.resolve(PUBLIC_DIR, file);
  if (!filePath.startsWith(path.resolve(PUBLIC_DIR)) || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) return send(res, 404, 'Not found');
  const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.png': 'image/png' };
  res.writeHead(200, { 'Content-Type': types[path.extname(filePath)] || 'application/octet-stream' });
  fs.createReadStream(filePath).pipe(res);
});

server.listen(PORT, HOST, () => console.log(`PFC API listening on http://${HOST}:${PORT}`));

module.exports = { server, readState, writeState };
