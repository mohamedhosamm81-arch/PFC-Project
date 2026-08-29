const KEY = 'pfc-clinic-v3';

const DESTINATIONS = [
  { key: 'Reception', label: 'Screen', ar: 'استقبال', icon: 'clipboard-list', tone: 'violet' },
  { key: 'CMO', label: 'Clinic', ar: 'العيادات', icon: 'stethoscope', tone: 'teal' },
  { key: 'Pharmacy', label: 'Pharmacy', ar: 'الصيدلية', icon: 'pill', tone: 'emerald' },
  { key: 'Laboratory', label: 'Laboratory', ar: 'المختبر', icon: 'flask-conical', tone: 'blue' },
  { key: 'Radiology', label: 'Radiology', ar: 'الأشعة', icon: 'scan-line', tone: 'orange' },
  { key: 'Cashier', label: 'Cashier', ar: 'الخزينة', icon: 'wallet-cards', tone: 'slate' }
];
const ORG_DEFAULT = 'وحدة طب أسرة العوامية';
const ALL_ROLES = ['Employee', 'Doctor', 'Receptionist', 'Manager'];
const BRANCHES = DESTINATIONS.map(d => d.key);
const ATTENDANCE_GRACE_MINUTES = 15;
const ORGANIZATION_DEPARTMENTS = ['Reception', 'CMO', 'Pharmacy', 'Laboratory', 'Radiology', 'Cashier'];

const isoDate = (date = new Date()) => date.toISOString().slice(0, 10);
const stamp = (time, date = isoDate()) => new Date(`${date}T${time}:00`).toISOString();
const today = () => isoDate();
const now = () => new Date().toISOString();
const fmt = value => value ? new Date(value).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';
const fmtTime = value => value ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—';
const initials = name => String(name || '').split(' ').map(x => x[0]).filter(Boolean).slice(0, 2).join('').toUpperCase();
const esc = value => String(value ?? '').replace(/[&<>'"]/g, ch => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#39;', '"':'&quot;' }[ch]));
const minutesFromTime = value => { const [h, m] = String(value || '08:00').split(':').map(Number); return (h * 60) + m; };
function latenessMinutes(start, shift = '08:00') {
  if (!start) return 0;
  const date = new Date(start);
  const actual = (date.getHours() * 60) + date.getMinutes();
  return Math.max(0, actual - minutesFromTime(shift) - ATTENDANCE_GRACE_MINUTES);
}

function createSeed() {
  const d = today();
  const users = [
    { name: 'System Manager', id: 'ADM-001', dept: 'Administration', org: ORG_DEFAULT, email: 'manager@eha.gov.eg', username: 'manager', password: 'manager123', role: 'Manager', shift: '08:00', availability: 'available', globalAdmin: true },
    { name: 'Reception Desk', id: 'REC-001', dept: 'Reception', org: ORG_DEFAULT, email: 'reception@eha.gov.eg', username: '2006159', password: '2005510', role: 'Receptionist', shift: '08:00', availability: 'available', setup: true },
    { name: 'Dr. Layla Hassan', id: 'DOC-101', dept: 'CMO', org: ORG_DEFAULT, email: 'layla@eha.gov.eg', username: 'doctor.layla', password: 'doctor123', role: 'Doctor', shift: '08:00', cmoSlot: 1, availability: 'available' },
    { name: 'Dr. Omar Nasser', id: 'DOC-102', dept: 'CMO', org: ORG_DEFAULT, email: 'omar@eha.gov.eg', username: 'doctor.omar', password: 'doctor123', role: 'Doctor', shift: '08:00', cmoSlot: 2, availability: 'available' },
    { name: 'Dr. Hala Saeed', id: 'DOC-103', dept: 'CMO', org: ORG_DEFAULT, email: 'hala@eha.gov.eg', username: 'doctor.hala', password: 'doctor123', role: 'Doctor', shift: '08:00', cmoSlot: 3, availability: 'unavailable' },
    { name: 'Sara Youssef', id: 'EHA-2077', dept: 'Pharmacy', org: ORG_DEFAULT, email: 'sara@eha.gov.eg', username: 'sara.youssef', password: 'demo123', role: 'Employee', shift: '08:00', availability: 'available' },
    { name: 'Mostafa Adel', id: 'EHA-3118', dept: 'Radiology', org: ORG_DEFAULT, email: 'mostafa@eha.gov.eg', username: 'mostafa.adel', password: 'demo123', role: 'Employee', shift: '08:00', availability: 'available' },
    { name: 'Nourhan Samir', id: 'EHA-4190', dept: 'Laboratory', org: ORG_DEFAULT, email: 'nourhan@eha.gov.eg', username: 'nourhan.samir', password: 'demo123', role: 'Employee', shift: '08:15', availability: 'available' }
  ];
  const patients = [
    { code: 245, service: 'CMO', branch: 'CMO', status: 'Done', late: false, created: stamp('08:02', d), assignedTo: 'DOC-101', history: [{ at: stamp('08:02', d), event: 'Issued', by: 'Reception Desk', destination: 'CMO' }, { at: stamp('08:25', d), event: 'Done', by: 'Dr. Layla Hassan', destination: 'CMO' }] },
    { code: 246, service: 'CMO', branch: 'CMO', status: 'Done', late: false, created: stamp('08:10', d), assignedTo: 'DOC-102', history: [{ at: stamp('08:10', d), event: 'Issued', by: 'Reception Desk', destination: 'CMO' }, { at: stamp('08:36', d), event: 'Done', by: 'Dr. Omar Nasser', destination: 'CMO' }] },
    { code: 247, service: 'CMO', branch: 'CMO', status: 'Serving', late: false, created: stamp('08:18', d), assignedTo: 'DOC-101', history: [{ at: stamp('08:18', d), event: 'Issued', by: 'Reception Desk', destination: 'CMO' }, { at: stamp('08:44', d), event: 'Called', by: 'Dr. Layla Hassan', destination: 'CMO' }] },
    { code: 248, service: 'CMO', branch: 'CMO', status: 'Waiting', late: false, created: stamp('08:29', d), assignedTo: null, history: [{ at: stamp('08:29', d), event: 'Issued', by: 'Reception Desk', destination: 'CMO' }] },
    { code: 249, service: 'CMO', branch: 'CMO', status: 'Waiting', late: true, created: stamp('08:34', d), assignedTo: null, history: [{ at: stamp('08:34', d), event: 'Issued', by: 'Reception Desk', destination: 'CMO' }] },
    { code: 201, service: 'Pharmacy', branch: 'Pharmacy', status: 'Done', late: false, created: stamp('08:05', d), assignedTo: 'EHA-2077', history: [{ at: stamp('08:05', d), event: 'Issued', by: 'Reception Desk', destination: 'Pharmacy' }, { at: stamp('08:31', d), event: 'Done', by: 'Sara Youssef', destination: 'Pharmacy' }] },
    { code: 202, service: 'Pharmacy', branch: 'Pharmacy', status: 'Serving', late: false, created: stamp('08:38', d), assignedTo: 'EHA-2077', history: [{ at: stamp('08:38', d), event: 'Issued', by: 'Reception Desk', destination: 'Pharmacy' }, { at: stamp('08:49', d), event: 'Called', by: 'Sara Youssef', destination: 'Pharmacy' }] },
    { code: 310, service: 'Laboratory', branch: 'Laboratory', status: 'Done', late: false, created: stamp('08:12', d), assignedTo: 'EHA-4190', history: [{ at: stamp('08:12', d), event: 'Issued', by: 'Reception Desk', destination: 'Laboratory' }, { at: stamp('08:43', d), event: 'Done', by: 'Nourhan Samir', destination: 'Laboratory' }] },
    { code: 311, service: 'Laboratory', branch: 'Laboratory', status: 'Waiting', late: false, created: stamp('08:47', d), assignedTo: 'EHA-4190', history: [{ at: stamp('08:47', d), event: 'Issued', by: 'Reception Desk', destination: 'Laboratory' }] },
    { code: 312, service: 'Radiology', branch: 'Radiology', status: 'Done', late: false, created: stamp('08:08', d), assignedTo: 'EHA-3118', history: [{ at: stamp('08:08', d), event: 'Issued', by: 'Reception Desk', destination: 'Radiology' }, { at: stamp('08:39', d), event: 'Done', by: 'Mostafa Adel', destination: 'Radiology' }] },
    { code: 313, service: 'Radiology', branch: 'Radiology', status: 'Waiting', late: false, created: stamp('08:55', d), assignedTo: 'EHA-3118', history: [{ at: stamp('08:55', d), event: 'Issued', by: 'Reception Desk', destination: 'Radiology' }] },
    { code: 88, service: 'Cashier', branch: 'Cashier', status: 'Waiting', late: false, created: stamp('08:22', d), assignedTo: null, history: [{ at: stamp('08:22', d), event: 'Transferred', by: 'Reception Desk', destination: 'Cashier' }]
    }
  ];
  return {
    version: 3,
    organizations: [{ id: 'ORG-001', name: ORG_DEFAULT, type: 'Health unit', location: 'العوامية', departments: [...ORGANIZATION_DEPARTMENTS], createdAt: stamp('07:45', d) }],
    users,
    currentUser: null,
    nextCode: 314,
    patients,
    sessions: users.filter(u => !['Manager', 'Receptionist'].includes(u.role)).map((u, i) => { const start = stamp(['08:01', '08:03', '08:06', '08:14', '08:07', '08:16'][i] || '08:00', d); return { userId: u.id, user: u.name, dept: u.dept, org: u.org, start, end: null, shift: u.shift, lateMinutes: latenessMinutes(start, u.shift) }; }),
    actions: [
      { user: 'Reception Desk', userId: 'REC-001', dept: 'Reception', type: 'Issue', code: 245, time: stamp('08:02', d), to: 'CMO' },
      { user: 'Dr. Layla Hassan', userId: 'DOC-101', dept: 'CMO', type: 'Done', code: 245, time: stamp('08:25', d), to: 'CMO' },
      { user: 'Dr. Omar Nasser', userId: 'DOC-102', dept: 'CMO', type: 'Done', code: 246, time: stamp('08:36', d), to: 'CMO' },
      { user: 'Sara Youssef', userId: 'EHA-2077', dept: 'Pharmacy', type: 'Done', code: 201, time: stamp('08:31', d), to: 'Pharmacy' },
      { user: 'Nourhan Samir', userId: 'EHA-4190', dept: 'Laboratory', type: 'Done', code: 310, time: stamp('08:43', d), to: 'Laboratory' },
      { user: 'Mostafa Adel', userId: 'EHA-3118', dept: 'Radiology', type: 'Done', code: 312, time: stamp('08:39', d), to: 'Radiology' }
    ],
    routing: { CMO: 3, Reception: 1, Pharmacy: 1, Laboratory: 1, Radiology: 1, Cashier: 1 },
    lastTicket: null
  };
}

function normalizeState(saved) {
  const fresh = createSeed();
  const merged = { ...fresh, ...saved, version: 3 };
  merged.organizations = (saved.organizations || fresh.organizations).map(org => ({ type: 'Health unit', location: '', departments: [...ORGANIZATION_DEPARTMENTS], services: [], ...org, services: org.services || [] }));
  merged.users = (saved.users || fresh.users).map(user => ({ availability: 'available', org: ORG_DEFAULT, ...user, globalAdmin: user.globalAdmin ?? (user.username === 'manager') }));
  merged.sessions = (saved.sessions || fresh.sessions).map(session => ({ ...session, lateMinutes: latenessMinutes(session.start, session.shift) }));
  merged.patients = (saved.patients || fresh.patients).map(patient => ({ late: false, history: [], assignedTo: null, org: ORG_DEFAULT, ...patient }));
  merged.actions = saved.actions || fresh.actions;
  merged.routing = { ...fresh.routing, ...(saved.routing || {}) };
  merged.nextCode = Math.min(999, Math.max(1, Math.floor(Number(saved.nextCode) || 1)));
  merged.patients.forEach(patient => { if (patient.branch === 'CMO' && patient.status === 'Waiting') patient.assignedTo = null; });
  return merged;
}

let state;
try {
  const saved = JSON.parse(localStorage.getItem(KEY) || 'null');
  state = saved && saved.version === 3 ? normalizeState(saved) : createSeed();
} catch (error) {
  state = createSeed();
}
  let page = 'overview';
  let displayMode = 'door';
  let reportPeriod = 'month';
  let kioskFullscreen = false;
let kioskCountdownTimer = null;

const ACCESS = {
  Manager: ['overview', 'displays', 'reports', 'activity', 'admin'],
  Receptionist: ['overview', 'kiosk', 'queues', 'sessions', 'activity'],
  Doctor: ['overview', 'queues', 'sessions', 'activity'],
  Employee: ['overview', 'queues', 'sessions', 'activity']
};
const canAccess = target => {
  const user = currentUser();
  if (!user) return false;
  if (user.setup && target !== 'kiosk') return false;
  return (ACCESS[user.role] || ACCESS.Employee).includes(target);
};
const save = () => localStorage.setItem(KEY, JSON.stringify(state));
const currentUser = () => state.currentUser;
const userById = id => state.users.find(user => user.id === id);
const destination = key => DESTINATIONS.find(item => item.key === key) || organizations().flatMap(org => org.services || []).find(item => item.key === key) || DESTINATIONS[0];
const displayName = key => destination(key).key === key ? destination(key).label : String(key || '—');
const patientByCode = code => state.patients.find(patient => Number(patient.code) === Number(code));
function isInManagerScope(record, user = currentUser()) {
  if (!user || user.role !== 'Manager' || user.globalAdmin) return true;
  const org = user.org || ORG_DEFAULT;
  if (record?.org) return (record.org || ORG_DEFAULT) === org;
  const actor = record?.userId ? userById(record.userId) : null;
  if (actor) return (actor.org || ORG_DEFAULT) === org;
  const patient = record?.code ? patientByCode(record.code) : null;
  return Boolean(patient && (patient.org || ORG_DEFAULT) === org);
}
const managerScope = (items, user = currentUser()) => items.filter(item => isInManagerScope(item, user));
const managerOrganizations = (user = currentUser()) => user?.role === 'Manager' && !user.globalAdmin ? organizations().filter(org => org.name === (user.org || ORG_DEFAULT)) : organizations();
const managerDestinations = (user = currentUser()) => { const list = user?.role === 'Manager' && !user.globalAdmin ? organizationDestinations(user.org) : allDestinations(); return list.filter((item, index, all) => all.findIndex(candidate => candidate.key === item.key) === index); };
const scopedPatients = (user = currentUser()) => managerScope(state.patients, user);
const scopedServedToday = (user = currentUser()) => scopedPatients(user).filter(patient => patient.status === 'Done' && isToday(patient.created)).length;
const scopedTotalServed = (user = currentUser()) => scopedPatients(user).filter(patient => patient.status === 'Done').length;
const isToday = value => value && String(value).slice(0, 10) === today();
const activePatients = () => state.patients.filter(patient => patient.status !== 'Done');
const servedToday = () => state.patients.filter(patient => patient.status === 'Done' && isToday(patient.created)).length;
const totalServed = () => state.patients.filter(patient => patient.status === 'Done').length;
const waitingFor = branch => state.patients.filter(patient => patient.branch === branch && patient.status === 'Waiting');
const activeSession = userId => [...state.sessions].reverse().find(session => session.userId === userId && !session.end);
const employees = () => managerScope(state.users.filter(user => user.role !== 'Manager' && user.dept !== 'Administration'));
const organizations = () => state.organizations || [{ id: 'ORG-001', name: ORG_DEFAULT, type: 'Health unit', location: 'العوامية', departments: [...ORGANIZATION_DEPARTMENTS] }];
const organizationByName = name => organizations().find(org => org.name === name);
const allDestinations = () => [...DESTINATIONS, ...organizations().flatMap(org => (org.services || []).map(service => ({ ...service, custom: true })))];
const organizationDestinations = orgName => { const org = organizationByName(orgName) || organizations()[0]; const enabled = new Set(org?.departments || ORGANIZATION_DEPARTMENTS); return [...DESTINATIONS.filter(item => enabled.has(item.key)), ...(org?.services || [])]; };
function periodStart() {
  const date = new Date();
  if (reportPeriod === 'week') date.setDate(date.getDate() - 6);
  else date.setDate(1);
  date.setHours(0, 0, 0, 0);
  return date;
}
function inReportPeriod(value) { return value && new Date(value) >= periodStart(); }

function icon(name, cls = 'h-4 w-4') { return `<i data-lucide="${name}" class="${cls}"></i>`; }
function btn(label, action, cls = 'bg-ink text-white hover:bg-slate-800', ic = '') { return `<button type="button" data-action="${action}" class="inline-flex items-center justify-center gap-2 rounded-xl px-3.5 py-2.5 text-sm font-semibold transition ${cls}">${ic ? icon(ic) : ''}${label}</button>`; }
function toneClasses(tone) {
  return { teal: 'bg-teal/10 text-teal', violet: 'bg-violet-50 text-violet-700', emerald: 'bg-emerald-50 text-emerald-700', blue: 'bg-blue-50 text-blue-700', orange: 'bg-orange-50 text-orange-700', slate: 'bg-slate-100 text-slate-700' }[tone] || 'bg-slate-100 text-slate-700';
}
function statusPill(status) {
  const map = { Waiting: ['bg-amber-50 text-amber-700', 'Waiting'], Serving: ['bg-teal/10 text-teal', 'Serving'], Done: ['bg-emerald-50 text-emerald-700', 'Done'], Late: ['bg-orange-50 text-orange-700', 'Late'] };
  const [cls, label] = map[status] || map.Waiting;
  return `<span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${cls}"><span class="h-1.5 w-1.5 rounded-full bg-current"></span>${label}</span>`;
}
function availabilityPill(user) {
  const available = user?.availability !== 'unavailable';
  return `<span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${available ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}"><span class="h-1.5 w-1.5 rounded-full bg-current"></span>${available ? 'Available' : 'Unavailable'}</span>`;
}
function toast(message, type = 'success') {
  const el = document.createElement('div');
  el.className = `fade flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium shadow-soft ${type === 'error' ? 'bg-red-50 text-red-700 border border-red-100' : 'bg-white text-slate-700 border border-slate-100'}`;
  el.innerHTML = `${icon(type === 'error' ? 'alert-circle' : 'check-circle-2')}<span>${esc(message)}</span>`;
  document.getElementById('toastRoot').appendChild(el);
  lucide.createIcons();
  setTimeout(() => el.remove(), 3400);
}
function pageTitle(target) {
  return ({ overview: 'Operations overview', kiosk: 'Screen ticket desk', queues: 'Queues & patient routing', displays: 'Live display boards', sessions: 'My session', reports: 'Reports & attendance', activity: 'Action sheet', admin: 'Admin dashboard' }[target] || 'Operations overview');
}
function nav() {
  const all = [
    ['overview', 'layout-dashboard', 'Workspace'], ['kiosk', 'ticket', 'Issue ticket'], ['queues', 'list-ordered', 'My queue'],
    ['displays', 'monitor-smartphone', 'Live displays'], ['sessions', 'clock-3', 'My session'], ['reports', 'chart-no-axes-combined', 'Reports'],
    ['activity', 'table-2', 'Action sheet'], ['admin', 'shield-check', 'Admin dashboard']
  ];
  const items = all.filter(([target]) => canAccess(target));
  document.getElementById('nav').innerHTML = items.map(([target, ic, label]) => `<button data-page="${target}" class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm ${page === target ? 'nav-active' : 'text-slate-300 hover:bg-white/10'}">${icon(ic)}<span>${label}</span>${target === 'queues' ? `<span class="ml-auto text-xs bg-white/10 rounded-full px-2 py-0.5">${activePatients().length}</span>` : ''}</button>`).join('');
  document.querySelectorAll('[data-page]').forEach(el => el.addEventListener('click', () => { page = el.dataset.page; render(); closeSidebar(); }));
  lucide.createIcons();
}
function shell() {
  document.getElementById('authView').classList.add('hidden');
  document.getElementById('appView').classList.remove('hidden');
  const user = currentUser();
  const sessionLocked = page === 'sessions' && user.role !== 'Manager' && user.role !== 'Receptionist' && !activeSession(user.id);
  document.getElementById('topUser').textContent = user.name;
  document.getElementById('topDept').textContent = `${user.role} · ${user.id} · ${displayName(user.dept)}`;
  document.getElementById('topAvatar').textContent = initials(user.name);
  const availability = document.getElementById('headerAvailability');
  availability.className = `status-pill ${user.availability === 'unavailable' ? 'status-unavailable' : 'status-available'}`;
  availability.innerHTML = `${icon(user.availability === 'unavailable' ? 'pause-circle' : 'circle-check')} ${user.availability === 'unavailable' ? 'Unavailable' : 'Available'}`;

  if (kioskFullscreen || sessionLocked) {
    document.getElementById('sidebar').classList.add('hidden');
    document.getElementById('contentShell').classList.remove('lg:pl-72');
    document.querySelector('header').classList.add('hidden');
  } else {
    document.getElementById('sidebar').classList.remove('hidden');
    document.getElementById('contentShell').classList.add('lg:pl-72');
    document.querySelector('header').classList.remove('hidden');
  }

  nav();
  lucide.createIcons();
}
function statCard(label, value, note, ic, tone = 'teal') {
  return `<div class="bg-white rounded-2xl p-5 shadow-soft border border-slate-100"><div class="flex items-start justify-between gap-3"><div><div class="text-sm text-slate-500">${label}</div><div class="text-3xl font-bold mt-2 text-ink">${value}</div><div class="text-xs text-slate-400 mt-2">${note}</div></div><div class="h-11 w-11 rounded-xl ${toneClasses(tone)} flex items-center justify-center">${icon(ic)}</div></div></div>`;
}
function hero(eyebrow, title, description, actions = '') {
  return `<div class="flex flex-col lg:flex-row lg:items-end justify-between gap-4 mb-7"><div><p class="text-teal font-semibold text-sm">${eyebrow}</p><h1 class="text-3xl font-bold mt-1">${title}</h1><p class="text-slate-500 mt-2 max-w-2xl">${description}</p></div><div class="flex flex-wrap gap-2">${actions}</div></div>`;
}
function sessionSummary() {
  const user = currentUser();
  const session = activeSession(user.id);
  const late = session?.lateMinutes || 0;
  return `<div class="bg-ink rounded-2xl shadow-soft p-5 text-white"><div class="flex items-center justify-between"><div><h2 class="font-bold">Your station session</h2><p class="text-slate-300 text-sm mt-1">${esc(displayName(user.dept))} · ${esc(user.org || ORG_DEFAULT)}</p></div>${icon('scan-line', 'h-5 w-5 text-teal-300')}</div><div class="mt-7 grid grid-cols-2 gap-4"><div><div class="text-xs text-slate-400">Started</div><div class="text-xl font-bold mt-1">${session ? fmtTime(session.start) : 'Not started'}</div></div><div><div class="text-xs text-slate-400">Lateness</div><div class="text-xl font-bold mt-1 ${late ? 'text-orange-300' : 'text-emerald-300'}">${late} min</div></div></div><button data-action="session-toggle" class="w-full mt-6 rounded-xl ${session ? 'bg-white/10 hover:bg-white/20' : 'bg-teal hover:bg-teal-700'} px-4 py-3 text-sm font-semibold">${session ? 'End session' : 'Start session'} ${icon(session ? 'log-out' : 'play')}</button></div>`;
}
function stationConsole() {
  const user = currentUser();
  const session = activeSession(user.id);
  if (!session && user.role !== 'Manager' && user.dept !== 'Administration') {
    return `<section class="bg-white rounded-3xl border border-slate-100 shadow-soft p-8 text-center max-w-2xl mx-auto my-12"><div class="h-20 w-20 rounded-3xl bg-teal/10 text-teal flex items-center justify-center mx-auto mb-6">${icon('play', 'h-10 w-10')}</div><h2 class="text-3xl font-bold">Start your session</h2><p class="text-slate-500 mt-4 text-lg">You must start a session to begin receiving patients at your station. Your start time and lateness will be recorded.</p><button data-action="session-toggle" class="mt-8 rounded-2xl bg-teal text-white px-8 py-4 text-lg font-bold hover:bg-teal-700 transition shadow-soft">Start working now ${icon('arrow-right')}</button></section>`;
  }
  const userOrg = user.org || ORG_DEFAULT;
  const myPatients = state.patients.filter(patient => user.dept === 'CMO' ? patient.assignedTo === user.id && patient.status === 'Serving' : patient.assignedTo === user.id && ['Waiting', 'Serving'].includes(patient.status));
  const serving = myPatients.find(patient => patient.status === 'Serving');
  const waiting = user.dept === 'CMO' ? state.patients.filter(patient => patient.branch === 'CMO' && (patient.org || ORG_DEFAULT) === userOrg && patient.status === 'Waiting' && !patient.assignedTo).length : myPatients.filter(patient => patient.status === 'Waiting').length;
  const canProcess = user.role !== 'Manager' && user.dept !== 'Administration';
  if (!canProcess) return `<div class="notice-card border border-slate-200 bg-white rounded-2xl p-5 mb-5"><div class="flex items-center gap-3"><div class="h-10 w-10 rounded-xl bg-teal/10 text-teal flex items-center justify-center">${icon('shield-check')}</div><div><b>Manager control center</b><p class="text-sm text-slate-500 mt-1">Use the admin dashboard and reports to supervise every destination and employee.</p></div></div></div>`;
  return `<section class="bg-white rounded-2xl border border-teal-100 shadow-soft p-5 sm:p-6 mb-5"><div class="flex flex-col xl:flex-row xl:items-center justify-between gap-5"><div><div class="flex items-center gap-2 text-teal text-sm font-semibold">${icon('scan-line')} ${user.dept === 'CMO' ? 'Clinic shared queue command center' : `${esc(displayName(user.dept))} command center`}</div><h2 class="text-xl font-bold mt-2">${serving ? `Now serving ticket #${serving.code}` : 'Ready for the next patient'}</h2><p class="text-sm text-slate-500 mt-1">Press <b>Next patient</b> to take the oldest eligible ticket. In Clinic, all three available employees draw from one shared organization queue.</p></div><div class="flex items-center gap-2">${availabilityPill(user)}<span class="rounded-xl bg-mist border border-slate-100 px-4 py-2.5 text-sm text-slate-600">${waiting} ${user.dept === 'CMO' ? 'in shared Clinic queue' : 'waiting for you'}</span></div></div>${serving ? `<div class="mt-5 rounded-2xl bg-teal/[.06] border border-teal/10 p-4 flex flex-col md:flex-row md:items-center justify-between gap-4"><div class="flex items-center gap-4"><div class="ticket-number ticket-number-sm">${serving.code}</div><div><div class="font-bold">Current patient</div><div class="text-sm text-slate-500">Issued ${fmt(serving.created)} · ${serving.late ? 'Marked late' : 'On time'}</div></div></div><div class="flex flex-wrap gap-2">${btn('Done', `patient-done-${serving.code}`, 'bg-emerald-600 text-white hover:bg-emerald-700', 'check')}${btn('Late', `patient-late-${serving.code}`, 'bg-yellow-400 text-ink hover:bg-yellow-500', 'clock-3')}${btn('Transfer', `patient-transfer-${serving.code}`, 'bg-white text-ink border border-slate-200 hover:border-teal', 'arrow-right-left')}${btn('Pause queue', 'availability-toggle', 'bg-white text-slate-700 border border-slate-200 hover:border-orange-300', 'pause')}</div></div>` : `<div class="mt-5 flex flex-col sm:flex-row gap-3"><button data-action="next-patient" class="rounded-xl bg-teal text-white px-5 py-3.5 font-semibold hover:bg-teal-700 transition">Next patient ${icon('arrow-right')}</button>${btn('Pause queue', 'availability-toggle', 'bg-white text-slate-700 border border-slate-200 hover:border-orange-300', 'pause')}<div class="text-sm text-slate-500 flex items-center gap-2 px-2">${icon('info')} ${user.availability === 'unavailable' ? 'Set yourself available to receive patients.' : 'No patient is currently assigned.'}</div></div>`}</section>`;
}
function overview() {
  const user = currentUser();
  const scope = user.role === 'Manager' ? managerScope(state.patients, user) : state.patients.filter(patient => (patient.org || ORG_DEFAULT) === (user.org || ORG_DEFAULT) && (patient.branch === user.dept || patient.assignedTo === user.id));
  const active = scope.filter(patient => patient.status !== 'Done');
  const done = scope.filter(patient => patient.status === 'Done' && isToday(patient.created)).length;
  const late = scope.filter(patient => patient.late && patient.status !== 'Done').length;
  const actions = user.role === 'Manager' ? [btn('Open reports', 'go-reports', 'bg-white border border-slate-200 text-ink hover:border-teal', 'chart-no-axes-combined')] : (user.role === 'Receptionist' ? [btn('Issue a ticket', 'go-kiosk', 'bg-teal text-white hover:bg-teal-700', 'ticket')] : []);
  const branchRows = managerDestinations(user).map(item => {
    const activeCount = active.filter(patient => patient.branch === item.key).length;
    const waiting = active.filter(patient => patient.branch === item.key && patient.status === 'Waiting').length;
    const people = employees().filter(employee => employee.dept === item.key);
    const available = people.filter(employee => employee.availability !== 'unavailable').length;
    const percent = Math.min(100, 14 + (activeCount * 18));
    return `<div class="py-3 border-b border-slate-100 last:border-0"><div class="flex items-center justify-between gap-3"><div class="flex items-center gap-3"><div class="h-9 w-9 rounded-xl ${toneClasses(item.tone)} flex items-center justify-center">${icon(item.icon)}</div><div><div class="font-semibold text-sm">${item.label}</div><div class="text-xs text-slate-400" dir="rtl">${item.ar}</div></div></div><div class="text-right"><div class="font-bold text-sm">${activeCount} active</div><div class="text-xs text-slate-400">${waiting} waiting · ${available}/${people.length || 0} online</div></div></div><div class="h-1.5 mt-3 rounded-full bg-slate-100 overflow-hidden"><div class="h-full rounded-full ${item.key === 'Pharmacy' ? 'bg-emerald-500' : item.key === 'Radiology' ? 'bg-orange-400' : 'bg-teal'}" style="width:${percent}%"></div></div></div>`;
  }).join('');
  return `<div class="fade">${hero(`Good morning, ${esc(user.name.split(' ')[0])}`, 'Operations overview', 'See today’s patient volume, employee availability, and routing health from one control room.', actions)}${stationConsole()}<div class="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">${statCard('Patients served today', done, 'Completed journeys today', 'badge-check', 'teal')}${statCard('Total served', scope.filter(patient => patient.status === 'Done').length, 'All completed journeys', 'users-round', 'blue')}${statCard('Waiting now', active.filter(patient => patient.status === 'Waiting').length, 'Ready to be called', 'clock-3', 'orange')}${statCard('Late in queue', late, 'Marked late and prioritized last', 'alarm-clock', 'orange')}</div><div class="grid xl:grid-cols-[1.25fr_.75fr] gap-5 mt-5"><div class="bg-white rounded-2xl border border-slate-100 shadow-soft p-5"><div class="flex items-start justify-between gap-3"><div><h2 class="font-bold">Live destination load</h2><p class="text-sm text-slate-500 mt-1">Queue health and employee capacity right now.</p></div>${user.role === 'Manager' ? btn('Open displays', 'go-displays', 'text-teal bg-teal/5 hover:bg-teal/10', 'monitor-smartphone') : ''}</div><div class="mt-4">${branchRows}</div></div>${sessionSummary()}</div></div>`;
}
function kiosk() {
  const last = state.lastTicket;
  const kioskActions = kioskFullscreen ? btn('Exit full screen', 'kiosk-exit', 'bg-ink text-white hover:bg-slate-800 px-5 py-3', 'minimize') : btn('Enter kiosk mode', 'kiosk-enter', 'bg-teal text-white hover:bg-teal-700', 'maximize');
  const kioskDestinations = organizationDestinations(currentUser().org).filter(item => item.key !== 'Cashier');
  const kioskClass = kioskFullscreen ? 'fixed inset-0 z-[100] bg-mist p-6 sm:p-8 overflow-y-auto' : 'fade max-w-6xl mx-auto';
  const destinationPanel = `<section class="bg-white border border-slate-100 rounded-3xl shadow-soft p-5 sm:p-7 ${kioskFullscreen ? 'max-w-6xl mx-auto' : ''}">
    <div class="flex items-center justify-between gap-3 mb-5">
      <div><h2 class="font-bold text-2xl">Where would you like to go?</h2><p class="text-lg text-slate-500 mt-1">من فضلك اختر الوجهة التي تريد الذهاب إليها</p></div>
      <span class="live-badge">LIVE ROUTING</span>
    </div>
    <div class="grid sm:grid-cols-2 ${kioskFullscreen ? 'xl:grid-cols-3' : ''} gap-4">
      ${kioskDestinations.map(item => `<button data-service="${item.key}" class="destination-button rounded-2xl p-6 text-left border border-slate-100 hover:border-teal/40 hover:-translate-y-0.5 transition">
        <div class="h-16 w-16 rounded-2xl ${toneClasses(item.tone)} flex items-center justify-center">${icon(item.icon, 'h-8 w-8')}</div>
        <div class="mt-6 flex items-end justify-between gap-3">
          <div><h3 class="font-bold text-xl">${item.label}</h3><div class="text-lg text-slate-500 mt-1" dir="rtl">${item.ar}</div></div>
          ${icon('arrow-up-right', 'h-6 w-6 text-slate-400')}
        </div>
      </button>`).join('')}
    </div>
  </section>`;
  if (kioskFullscreen) return `<div class="${kioskClass}"><div class="flex justify-between items-center mb-8 max-w-6xl mx-auto"><div class="flex items-center gap-3"><div class="h-12 w-12 rounded-2xl bg-white flex items-center justify-center overflow-hidden p-1 shadow-soft"><img src="eha-logo-mark.png" alt="EHA" class="h-full w-full object-contain" /></div><div><div class="font-bold text-xl">PFC Kiosk</div><div class="text-xs text-slate-500">وحدة طب أسرة العوامية</div></div></div>${kioskActions}</div>${destinationPanel}</div>`;
  return `<div class="${kioskClass}">${hero('Screen / استقبال', 'Issue a patient ticket', 'Choose the destination the patient needs. PFC creates a unique code and routes it to the fairest available employee automatically.', kioskActions)}<div class="grid lg:grid-cols-[1.2fr_.8fr] gap-5">${destinationPanel}<section class="bg-ink rounded-3xl shadow-soft p-8 text-white min-h-[400px] flex flex-col justify-between"><div><div class="flex items-center gap-2 text-teal-300 text-lg font-semibold">${icon('ticket', 'h-6 w-6')} Latest issued ticket</div><div class="mt-12 text-center">${last ? `<div class="text-slate-300 text-lg">${esc(destination(last.service).label)} · ${fmt(last.created)}</div><div class="ticket-number ticket-number-lg mx-auto mt-6">${last.code}</div><div class="mt-6">${statusPill(last.status)}</div>` : `<div class="h-48 flex items-center justify-center text-slate-400 text-lg">No ticket issued yet.</div>`}</div></div><div class="flex gap-3 mt-8">${last ? btn('Print ticket', 'print-ticket', 'bg-white/10 text-white hover:bg-white/20 flex-1 py-4 text-lg', 'printer') : ''}${btn('View queue', 'go-queues', 'bg-teal text-white hover:bg-teal-700 flex-1 py-4 text-lg', 'list-ordered')}</div></section></div></div>`;
}
function ticketRow(patient, showAssignment = true) {
  const assigned = userById(patient.assignedTo);
  const label = destination(patient.branch).label;
  const shared = patient.branch === 'CMO' && !assigned;
  return `<div class="patient-row flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 border-b border-slate-100 last:border-0" data-search="${esc(`${patient.code} ${label} ${patient.branch} ${patient.status} ${assigned?.name || ''}`.toLowerCase())}"><div class="flex items-center gap-4"><div class="ticket-number ticket-number-xs">${patient.code}</div><div><div class="font-semibold">${esc(label)}</div><div class="text-xs text-slate-400 mt-1">${shared ? 'Shared Clinic queue' : assigned ? `Assigned to ${esc(assigned.name)}` : 'Awaiting assignment'} · Issued ${fmt(patient.created)}${patient.late ? ' · marked late' : ''}</div></div></div><div class="flex items-center gap-3 flex-wrap">${showAssignment && !shared ? `<span class="text-xs text-slate-500">${assigned ? `Assigned to ${esc(assigned.name)}` : 'Awaiting assignment'}</span>` : ''}${statusPill(patient.status)}${patient.status !== 'Done' && currentUser().role !== 'Manager' ? `<button data-patient-view="${patient.code}" class="text-teal text-sm font-semibold">Open ${icon('arrow-up-right')}</button>` : ''}</div></div>`;
}
function queues() {
  const user = currentUser();
  const visible = user.role === 'Manager' ? managerDestinations(user).map(item => item.key) : [user.dept];
  const userOrg = user.org || ORG_DEFAULT;
  const branches = visible.map(branch => {
    const item = destination(branch);
    const patients = state.patients.filter(patient => patient.branch === branch && (user.role === 'Manager' || (patient.org || ORG_DEFAULT) === userOrg) && patient.status !== 'Done').sort((a, b) => (a.status === 'Serving' ? -1 : 1) - (b.status === 'Serving' ? -1 : 1) || Number(a.late) - Number(b.late) || new Date(a.created) - new Date(b.created));
    return `<section class="bg-white rounded-2xl border border-slate-100 shadow-soft overflow-hidden"><div class="p-5 border-b border-slate-100 flex items-center justify-between gap-3"><div class="flex items-center gap-3"><div class="h-10 w-10 rounded-xl ${toneClasses(item.tone)} flex items-center justify-center">${icon(item.icon)}</div><div><h2 class="font-bold">${item.label}</h2><p class="text-xs text-slate-400" dir="rtl">${item.ar}</p></div></div><div class="text-right"><div class="font-bold">${patients.length}</div><div class="text-xs text-slate-400">active</div></div></div><div>${patients.map(patient => ticketRow(patient, user.role === 'Manager' || patient.assignedTo !== user.id)).join('') || '<div class="p-6 text-center text-sm text-slate-400">No active patients in this queue.</div>'}</div></section>`;
  }).join('');
  return `<div class="fade">${hero('Core queue system', 'Queues & patient routing', 'Every patient keeps one unique code while the routing engine coordinates the right available employee.', `${btn('Refresh', 'refresh', 'bg-white border border-slate-200 text-ink hover:border-teal', 'refresh-cw')}`)}<div class="flex flex-col sm:flex-row gap-3 mb-5"><div class="relative flex-1"><span class="absolute left-3 top-3 text-slate-400">${icon('search')}</span><input id="queueSearch" class="w-full rounded-xl border border-slate-200 pl-10 pr-4 py-3 text-sm" placeholder="Search ticket, destination, status, or employee" /></div><div class="rounded-xl bg-teal/5 border border-teal/10 px-4 py-3 text-sm text-teal flex items-center gap-2">${icon('route')} Auto-routing active</div></div><div class="grid xl:grid-cols-2 gap-5">${branches}</div></div>`;
}
function displayCard(item) {
  const viewer = currentUser();
  const visiblePatients = scopedPatients(viewer);
  const patients = visiblePatients.filter(patient => patient.branch === item.key);
  const current = patients.find(patient => patient.status === 'Serving');
  const waiting = patients.filter(patient => patient.status === 'Waiting');
  const people = state.users.filter(user => user.dept === item.key && (user.org || ORG_DEFAULT) === (viewer.org || ORG_DEFAULT) && user.role !== 'Manager');
  return `<div class="display-card bg-white rounded-2xl border border-slate-100 shadow-soft overflow-hidden"><div class="p-4 border-b border-slate-100 flex justify-between items-center"><div class="flex items-center gap-2"><span class="h-2.5 w-2.5 rounded-full ${people.some(person => person.availability !== 'unavailable') ? 'bg-emerald-500' : 'bg-slate-300'}"></span><b>${item.label}</b></div><span class="text-xs text-slate-400">${people.filter(person => person.availability !== 'unavailable').length}/${people.length} available</span></div><div class="p-5"><div class="text-xs text-slate-400 uppercase tracking-wider">Now serving</div><div class="display-code mt-2">${current ? current.code : '—'}</div><div class="text-sm text-slate-500 mt-2">${current ? `Please proceed to ${item.label}` : 'Waiting for the next call'}</div><div class="mt-5 pt-4 border-t border-slate-100 flex justify-between items-center"><span class="text-sm text-slate-500">Waiting queue</span><span class="font-bold text-lg">${waiting.length}</span></div>${waiting.slice(0, 4).map(patient => `<div class="flex items-center justify-between py-2 text-sm"><span class="font-semibold">#${patient.code}</span>${patient.late ? '<span class="text-xs text-orange-600">Late</span>' : '<span class="text-xs text-slate-400">Waiting</span>'}</div>`).join('')}</div></div>`;
}
function displays() {
  const modeButtons = `<div class="inline-flex rounded-xl border border-slate-200 p-1 bg-white">${[['door', 'Door screen', 'door-open'], ['floor', 'Floor overview', 'layout-grid']].map(([mode, label, ic]) => `<button id="${mode}Mode" data-display-mode="${mode}" class="rounded-lg px-3 py-2 text-sm font-semibold ${displayMode === mode ? 'bg-ink text-white' : 'text-slate-500 hover:bg-mist'}">${icon(ic)} ${label}</button>`).join('')}</div>`;
  if (displayMode === 'door') {
    const doorCards = managerDestinations(currentUser()).filter(item => item.key !== 'Reception').map(displayCard).join('');
    return `<div class="fade">${hero('Patient-facing visibility', 'Door screen', 'A clear, live board for every destination. The served count at the top shows today’s completed patients.', modeButtons)}<div class="grid sm:grid-cols-3 gap-4 mb-5">${statCard('Patients served today', scopedServedToday(), 'This organization', 'badge-check', 'teal')}${statCard('Total served', scopedTotalServed(), 'Historical completed journeys', 'users-round', 'blue')}${statCard('Waiting now', scopedPatients(currentUser()).filter(patient => patient.status === 'Waiting').length, 'Across this organization', 'clock-3', 'orange')}</div><div class="rounded-3xl bg-ink text-white p-6 sm:p-8 mb-5 shadow-soft"><div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4"><div><div class="text-teal-300 text-sm font-semibold flex items-center gap-2">${icon('radio')} LIVE CALL BOARD</div><h2 class="text-2xl font-bold mt-2">Please follow your ticket to the displayed door</h2><p class="text-slate-300 mt-2">Ticket numbers update automatically after an employee presses Next patient.</p></div><div class="text-right"><div class="text-xs text-slate-400">Updated</div><div class="font-semibold">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div></div></div></div><div class="grid xl:grid-cols-2 gap-5">${doorCards}</div></div>`;
  }
  const scoped = scopedPatients(currentUser());
  const summary = managerDestinations(currentUser()).map(item => { const active = scoped.filter(patient => patient.branch === item.key && patient.status !== 'Done'); const waiting = active.filter(patient => patient.status === 'Waiting'); return `<div class="bg-white rounded-2xl border border-slate-100 shadow-soft p-5"><div class="flex justify-between items-center"><div class="font-semibold">${item.label}</div><span class="text-xs text-slate-400">${active.length} active</span></div><div class="mt-4 h-2 rounded-full bg-slate-100 overflow-hidden"><div class="h-full bg-teal rounded-full" style="width:${Math.min(100, 15 + waiting.length * 20)}%"></div></div><div class="grid grid-cols-2 gap-3 mt-4 text-sm"><div><div class="text-xs text-slate-400">Serving</div><b>${active.filter(patient => patient.status === 'Serving').map(patient => `#${patient.code}`).join(', ') || '—'}</b></div><div><div class="text-xs text-slate-400">Waiting</div><b>${waiting.length}</b></div></div></div>`; }).join('');
  return `<div class="fade">${hero('Patient-facing visibility', 'Floor overview', 'A manager-friendly view of queue load and service availability by destination.', modeButtons)}<div class="grid sm:grid-cols-2 xl:grid-cols-3 gap-5">${summary}</div></div>`;
}
function attendanceTable(mine) {
  return `<div class="bg-white rounded-2xl border border-slate-100 shadow-soft overflow-hidden"><div class="p-5 border-b border-slate-100"><h2 class="font-bold">Recent attendance</h2><p class="text-sm text-slate-500 mt-1">Session start, end, and lateness are recorded for reporting.</p></div><div class="overflow-x-auto"><table class="w-full text-sm"><thead class="bg-mist text-slate-500"><tr><th class="text-left p-4">Date</th><th class="text-left p-4">Started</th><th class="text-left p-4">Ended</th><th class="text-left p-4">Late</th></tr></thead><tbody>${mine.slice(0, 8).map(session => `<tr class="border-t border-slate-100"><td class="p-4">${new Date(session.start).toLocaleDateString()}</td><td class="p-4 font-semibold">${fmtTime(session.start)}</td><td class="p-4">${session.end ? fmtTime(session.end) : '<span class="text-teal font-semibold">Active</span>'}</td><td class="p-4">${session.lateMinutes ? `<span class="text-orange-600 font-semibold">${session.lateMinutes} min</span>` : '<span class="text-emerald-600">On time</span>'}</td></tr>`).join('') || '<tr><td colspan="4" class="p-8 text-center text-slate-400">No session history yet.</td></tr>'}</tbody></table></div></div>`;
}
function sessions() {
  const user = currentUser();
  const mine = state.sessions.filter(session => session.userId === user.id).sort((a, b) => new Date(b.start) - new Date(a.start));
  const current = activeSession(user.id);
  const late = mine.reduce((sum, session) => sum + (session.lateMinutes || 0), 0);
  if (!current && user.role !== 'Manager' && user.role !== 'Receptionist') {
    return `<div class="session-start-page"><div class="session-start-brand"><div class="h-14 w-14 rounded-2xl bg-white flex items-center justify-center overflow-hidden p-1 shadow-soft"><img src="eha-logo-mark.png" alt="EHA" class="h-full w-full object-contain" /></div><div><div class="font-bold text-xl">PFC Operations</div><div class="text-xs text-slate-400 uppercase tracking-widest">${esc(user.org || ORG_DEFAULT)}</div></div></div><div class="session-start-card"><div class="h-20 w-20 rounded-3xl bg-teal/10 text-teal flex items-center justify-center mx-auto">${icon('play', 'h-10 w-10')}</div><p class="text-teal font-semibold text-sm mt-7">${esc(displayName(user.dept))} station</p><h1 class="text-4xl font-bold mt-2">Start your session</h1><p class="text-slate-500 text-lg mt-4 max-w-md mx-auto">Welcome, ${esc(user.name)}. Start your shift to become available and receive patients. Your start time and lateness will be recorded automatically.</p><div class="grid grid-cols-2 gap-3 max-w-sm mx-auto mt-7 text-left"><div class="rounded-2xl bg-mist p-4"><div class="text-xs text-slate-400">Shift starts</div><b class="block mt-1">${esc(user.shift || '08:00')}</b></div><div class="rounded-2xl bg-mist p-4"><div class="text-xs text-slate-400">Station status</div><b class="block mt-1 text-slate-500">Unavailable</b></div></div><button data-action="session-toggle" class="mt-8 rounded-2xl bg-teal text-white px-10 py-4 text-lg font-bold hover:bg-teal-700 transition shadow-soft">Start working now ${icon('arrow-right')}</button><p class="text-xs text-slate-400 mt-5">You can pause or end the session at any time.</p></div>${attendanceTable(mine)}</div>`;
  }
  return `<div class="fade">${hero('Time & availability', 'My session', 'Start or end your station session and keep your availability visible to the whole routing system.', `${btn(user.availability === 'unavailable' ? 'Set available' : 'Set unavailable', 'availability-toggle', user.availability === 'unavailable' ? 'bg-teal text-white hover:bg-teal-700' : 'bg-white border border-slate-200 text-ink hover:border-orange-300', user.availability === 'unavailable' ? 'circle-check' : 'pause')}`)}<div class="grid lg:grid-cols-[.8fr_1.2fr] gap-5"><div class="bg-white rounded-2xl border border-slate-100 shadow-soft p-6"><div class="flex items-center justify-between"><div><div class="text-sm text-slate-500">Current status</div><div class="text-2xl font-bold mt-2">${user.availability === 'unavailable' ? 'Unavailable' : 'Available'}</div></div>${availabilityPill(user)}</div><div class="grid grid-cols-2 gap-4 mt-8"><div class="rounded-2xl bg-mist p-4"><div class="text-xs text-slate-400">Active session</div><div class="font-bold mt-2">${current ? fmtTime(current.start) : 'Not started'}</div></div><div class="rounded-2xl bg-mist p-4"><div class="text-xs text-slate-400">Lateness this month</div><div class="font-bold mt-2 ${late ? 'text-orange-600' : 'text-emerald-600'}">${late} minutes</div></div></div><button data-action="session-toggle" class="w-full mt-7 rounded-xl bg-ink text-white px-4 py-3.5 font-semibold hover:bg-slate-800">${current ? 'End session' : 'Start session'} ${icon(current ? 'log-out' : 'play')}</button></div><div class="bg-white rounded-2xl border border-slate-100 shadow-soft overflow-hidden"><div class="p-5 border-b border-slate-100"><h2 class="font-bold">Recent attendance</h2><p class="text-sm text-slate-500 mt-1">Session start, end, and lateness are recorded for reporting.</p></div><div class="overflow-x-auto"><table class="w-full text-sm"><thead class="bg-mist text-slate-500"><tr><th class="text-left p-4">Date</th><th class="text-left p-4">Started</th><th class="text-left p-4">Ended</th><th class="text-left p-4">Late</th></tr></thead><tbody>${mine.slice(0, 8).map(session => `<tr class="border-t border-slate-100"><td class="p-4">${new Date(session.start).toLocaleDateString()}</td><td class="p-4 font-semibold">${fmtTime(session.start)}</td><td class="p-4">${session.end ? fmtTime(session.end) : '<span class="text-teal font-semibold">Active</span>'}</td><td class="p-4">${session.lateMinutes ? `<span class="text-orange-600 font-semibold">${session.lateMinutes} min</span>` : '<span class="text-emerald-600">On time</span>'}</td></tr>`).join('') || '<tr><td colspan="4" class="p-8 text-center text-slate-400">No session history yet.</td></tr>'}</tbody></table></div></div></div></div>`;
}
function reportRows() {
  return employees().map(user => {
    const records = state.sessions.filter(session => session.userId === user.id && inReportPeriod(session.start));
    const active = records.find(record => !record.end);
    const minutes = records.reduce((sum, record) => sum + latenessMinutes(record.start, record.shift), 0);
    const served = state.patients.filter(patient => patient.assignedTo === user.id && patient.status === 'Done' && isToday(patient.created)).length;
    return { user, records, active, minutes, served };
  });
}
function reports() {
  const rows = reportRows();
  const totalLate = rows.reduce((sum, row) => sum + row.minutes, 0);
  const onDuty = employees().filter(user => user.availability !== 'unavailable').length;
  return `<div class="fade">${hero('Manager reporting', 'Reports & attendance', 'Review every employee’s session start, end, lateness, and service volume. Use the export button to create a printable PDF report.', btn('Export PDF report', 'export-pdf', 'bg-ink text-white hover:bg-slate-800', 'file-down'))}<div class="grid sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-5">${statCard('Employees tracked', employees().length, 'Across this organization', 'users', 'teal')}${statCard('Online now', onDuty, 'Available stations', 'wifi', 'emerald')}${statCard('Lateness this period', `${totalLate} min`, 'Recorded session delays', 'alarm-clock', 'orange')}${statCard('Served today', scopedServedToday(), 'This organization', 'badge-check', 'blue')}</div><div class="bg-white rounded-2xl border border-slate-100 shadow-soft overflow-hidden"><div class="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3"><div><h2 class="font-bold">Employee attendance and performance</h2><p class="text-sm text-slate-500 mt-1">Review when every employee started and ended, how late they were, and how much they served.</p></div><div class="flex flex-wrap gap-2"><select id="reportPeriod" class="rounded-xl border border-slate-200 px-3 py-2.5 text-sm"><option value="month" ${reportPeriod === 'month' ? 'selected' : ''}>This month</option><option value="week" ${reportPeriod === 'week' ? 'selected' : ''}>This week</option></select><input id="reportFilter" class="rounded-xl border border-slate-200 px-4 py-2.5 text-sm" placeholder="Filter employee or place" /></div></div><div class="overflow-x-auto"><table class="w-full text-sm"><thead class="bg-mist text-slate-500"><tr><th class="text-left p-4">Employee</th><th class="text-left p-4">Organization / place</th><th class="text-left p-4">Started</th><th class="text-left p-4">Ended</th><th class="text-left p-4">Late</th><th class="text-left p-4">Served</th><th class="text-left p-4">Status</th></tr></thead><tbody>${rows.map(row => `<tr class="report-row border-t border-slate-100" data-search="${esc(`${row.user.name} ${row.user.dept} ${row.user.org}`.toLowerCase())}"><td class="p-4"><div class="font-semibold">${esc(row.user.name)}</div><div class="text-xs text-slate-400">${esc(row.user.id)} · ${esc(row.user.role)}</div></td><td class="p-4"><div>${esc(row.user.org || ORG_DEFAULT)}</div><div class="text-xs text-slate-400">${esc(displayName(row.user.dept))}</div></td><td class="p-4">${row.active ? fmt(row.active.start) : row.records[0] ? fmt(row.records[0].start) : '—'}</td><td class="p-4">${row.active ? '<span class="text-teal font-semibold">Active</span>' : row.records[0]?.end ? fmt(row.records[0].end) : '—'}</td><td class="p-4">${row.minutes ? `<span class="font-semibold text-orange-600">${row.minutes} min</span>` : '<span class="text-emerald-600">On time</span>'}</td><td class="p-4 font-bold">${row.served}</td><td class="p-4">${availabilityPill(row.user)}</td></tr>`).join('') || '<tr><td colspan="7" class="p-8 text-center text-slate-400">No employees found.</td></tr>'}</tbody></table></div></div></div>`;
}
function activityRows() {
  const rows = state.actions.map(action => ({ time: action.time, user: action.user, userId: action.userId, org: action.org || (action.userId && userById(action.userId)?.org) || ORG_DEFAULT, dept: displayName(action.dept), type: action.type, code: action.code || '—', destination: displayName(action.to || action.dept) }));
  state.sessions.forEach(session => { rows.push({ time: session.start, user: session.user, userId: session.userId, org: session.org || userById(session.userId)?.org || ORG_DEFAULT, dept: displayName(session.dept), type: 'Start session', code: '—', destination: displayName(session.dept) }); if (session.end) rows.push({ time: session.end, user: session.user, userId: session.userId, org: session.org || userById(session.userId)?.org || ORG_DEFAULT, dept: displayName(session.dept), type: 'End session', code: '—', destination: displayName(session.dept) }); });
  return rows.sort((a, b) => new Date(b.time) - new Date(a.time));
}
function activity() {
  const rows = activityRows().filter(row => currentUser().role === 'Manager' ? isInManagerScope(row, currentUser()) : row.user === currentUser().name);
  return `<div class="fade">${hero('Audit-ready operational record', 'Action sheet', 'A chronological record of ticket actions, transfers, and employee session events.', '')}<div class="flex flex-col sm:flex-row gap-3 mb-5"><div class="relative flex-1"><span class="absolute left-3 top-3 text-slate-400">${icon('search')}</span><input id="activityFilter" class="w-full rounded-xl border border-slate-200 pl-10 pr-4 py-3 text-sm" placeholder="Filter by employee, action, destination, or ticket" /></div><div class="rounded-xl bg-mist px-4 py-3 text-sm text-slate-500">${rows.length} events</div></div><div class="bg-white border border-slate-100 shadow-soft rounded-2xl overflow-hidden"><div class="overflow-x-auto"><table class="w-full text-sm"><thead class="bg-mist text-slate-500"><tr><th class="text-left p-4">Time</th><th class="text-left p-4">Employee</th><th class="text-left p-4">Place</th><th class="text-left p-4">Ticket</th><th class="text-left p-4">Action</th><th class="text-left p-4">Destination</th></tr></thead><tbody>${rows.map(row => `<tr class="activity-row border-t border-slate-100" data-search="${esc(`${row.user} ${row.dept} ${row.type} ${row.code} ${row.destination}`.toLowerCase())}"><td class="p-4 whitespace-nowrap">${fmt(row.time)}</td><td class="p-4 font-semibold">${esc(row.user)}</td><td class="p-4 text-slate-500">${esc(row.dept)}</td><td class="p-4 font-bold">${esc(row.code)}</td><td class="p-4"><span class="rounded-full px-2.5 py-1 text-xs ${row.type === 'Done' ? 'bg-emerald-50 text-emerald-700' : row.type === 'Late' ? 'bg-orange-50 text-orange-700' : row.type === 'Transfer' ? 'bg-violet-50 text-violet-700' : 'bg-blue-50 text-blue-700'}">${esc(row.type)}</span></td><td class="p-4 text-slate-500">${esc(row.destination)}</td></tr>`).join('') || '<tr><td colspan="6" class="p-8 text-center text-slate-400">No actions recorded yet.</td></tr>'}</tbody></table></div></div></div>`;
}
function organizationSetupPanel() {
  const user = currentUser();
  if (!user?.globalAdmin) return `<section class="bg-amber-50 border border-amber-100 rounded-2xl p-5 mb-5"><div class="flex items-start gap-3"><div class="h-10 w-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center">${icon('building-2')}</div><div><h2 class="font-bold text-amber-900">Organization administration</h2><p class="text-sm text-amber-800 mt-1">This area is managed by the central administrator. Your manager account is assigned to ${esc(user.org || ORG_DEFAULT)}.</p></div></div></section>`;
  const departmentLabels = { Reception: 'Screen · استقبال', CMO: 'Clinic · العيادات', Pharmacy: 'Pharmacy · الصيدلية', Laboratory: 'Laboratory · المختبر', Radiology: 'Radiology · الأشعة', Cashier: 'Cashier · الخزينة' };
  return `<section class="bg-white rounded-2xl border border-slate-100 shadow-soft p-5 sm:p-6 mb-5"><div class="flex items-start justify-between gap-4"><div><div class="flex items-center gap-3"><div class="h-10 w-10 rounded-xl bg-violet-50 text-violet-700 flex items-center justify-center">${icon('building-2')}</div><div><h2 class="font-bold">Create a hospital or health unit</h2><p class="text-sm text-slate-500 mt-1">Create the organization first, then assign its manager and the departments it supports.</p></div></div></div><span class="live-badge">CENTRAL ADMIN</span></div><form id="organizationForm" class="grid lg:grid-cols-2 gap-4 mt-6"><div class="space-y-3"><label class="text-sm font-semibold">Hospital or health-unit name<input name="name" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="e.g. مستشفى القطيف العام" /></label><div class="grid sm:grid-cols-2 gap-3"><label class="text-sm font-semibold">Organization type<select name="type" class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3"><option>Health unit</option><option>Hospital</option></select></label><label class="text-sm font-semibold">Location<input name="location" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="City or district" /></label></div><div><div class="text-sm font-semibold mb-2">Departments and services</div><div class="grid sm:grid-cols-2 gap-2">${ORGANIZATION_DEPARTMENTS.map(dept => `<label class="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm"><input type="checkbox" name="departments" value="${dept}" checked />${departmentLabels[dept]}</label>`).join('')}</div></div></div><div class="space-y-3"><div class="rounded-2xl bg-mist p-4"><div class="font-semibold">Assigned manager account</div><p class="text-xs text-slate-500 mt-1">This manager will sign in and supervise this organization.</p></div><label class="text-sm font-semibold">Manager full name<input name="managerName" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="Manager name" /></label><div class="grid sm:grid-cols-2 gap-3"><label class="text-sm font-semibold">Manager staff ID<input name="managerId" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="ADM-000" /></label><label class="text-sm font-semibold">Manager username<input name="managerUsername" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="manager.unit" /></label></div><div class="grid sm:grid-cols-2 gap-3"><label class="text-sm font-semibold">Email<input name="managerEmail" type="email" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="manager@eha.gov.eg" /></label><label class="text-sm font-semibold">Password<input name="managerPassword" type="password" minlength="6" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="Minimum 6 characters" /></label></div><button class="w-full rounded-xl bg-violet-700 text-white py-3.5 font-semibold hover:bg-violet-800">Create organization and manager ${icon('arrow-right')}</button></div></form><div class="mt-6 pt-5 border-t border-slate-100"><h3 class="font-semibold">Existing hospitals and health units</h3><div class="grid md:grid-cols-2 xl:grid-cols-3 gap-3 mt-3">${organizations().map(org => { const manager = state.users.find(item => item.role === 'Manager' && item.org === org.name); return `<div class="rounded-2xl bg-mist p-4"><div class="flex items-start justify-between gap-2"><div><div class="font-semibold">${esc(org.name)}</div><div class="text-xs text-slate-500 mt-1">${esc(org.type)} · ${esc(org.location || 'Location not set')}</div></div><span class="text-xs rounded-full bg-white px-2 py-1 text-slate-500">${(org.departments || []).length} services</span></div><div class="text-sm mt-4"><span class="text-slate-400">Manager</span><div class="font-semibold">${manager ? esc(manager.name) : 'Not assigned'}</div></div><div class="text-xs text-slate-500 mt-2">${(org.departments || []).map(dept => esc(departmentLabels[dept] || displayName(dept))).join(' · ')}</div></div>`; }).join('')}</div></div></section>`;
}
function departmentServicesPanel() {
  const user = currentUser();
  if (!user?.globalAdmin) return `<section class="bg-amber-50 border border-amber-100 rounded-2xl p-5 mb-5"><div class="flex items-start gap-3"><div class="h-10 w-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center">${icon('layers-3')}</div><div><h2 class="font-bold text-amber-900">Departments & services</h2><p class="text-sm text-amber-800 mt-1">Only the central administrator can add new departments or services. Ask your central administrator to update ${esc(user.org || ORG_DEFAULT)}.</p></div></div></section>`;
  const labels = { Reception: 'Screen · استقبال', CMO: 'Clinic · العيادات', Pharmacy: 'Pharmacy · الصيدلية', Laboratory: 'Laboratory · المختبر', Radiology: 'Radiology · الأشعة', Cashier: 'Cashier · الخزينة' };
  const orgOptions = organizations().map(org => `<option value="${esc(org.name)}">${esc(org.name)}</option>`).join('');
  const directory = organizations().map(org => { const custom = org.services || []; const enabled = (org.departments || []).map(key => labels[key] || displayName(key)); return `<div class="rounded-2xl bg-mist p-4"><div class="flex items-start justify-between gap-3"><div><div class="font-semibold">${esc(org.name)}</div><div class="text-xs text-slate-500 mt-1">${esc(org.type)} · ${esc(org.location || 'Location not set')}</div></div><span class="text-xs rounded-full bg-white px-2 py-1 text-slate-500">${enabled.length + custom.length} total</span></div><div class="flex flex-wrap gap-2 mt-4">${enabled.map(label => `<span class="rounded-full bg-white px-2.5 py-1 text-xs text-slate-600">${esc(label)}</span>`).join('')}${custom.map(service => `<span class="rounded-full bg-violet-50 px-2.5 py-1 text-xs text-violet-700">${esc(service.label)}${service.ar ? ` · ${esc(service.ar)}` : ''}</span>`).join('')}${!enabled.length && !custom.length ? '<span class="text-sm text-slate-400">No departments yet.</span>' : ''}</div></div>`; }).join('');
  return `<section class="bg-white rounded-2xl border border-slate-100 shadow-soft p-5 sm:p-6 mb-5"><div class="flex items-start justify-between gap-4"><div><div class="flex items-center gap-3"><div class="h-10 w-10 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center">${icon('layers-3')}</div><div><h2 class="font-bold">Departments & services</h2><p class="text-sm text-slate-500 mt-1">Add a department or service to a hospital or health unit. It will become available for employee accounts, queues, and patient tickets.</p></div></div></div><span class="live-badge">CENTRAL ADMIN</span></div><form id="serviceForm" class="grid lg:grid-cols-[.9fr_1.1fr] gap-4 mt-6"><div class="space-y-3"><label class="text-sm font-semibold">Hospital or health unit<select name="org" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3">${orgOptions}</select></label><div class="grid sm:grid-cols-2 gap-3"><label class="text-sm font-semibold">Add type<select name="kind" class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3"><option>Department</option><option>Service</option></select></label><label class="text-sm font-semibold">Internal key<input name="key" class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="e.g. Cardiology" /></label></div></div><div class="space-y-3"><div class="grid sm:grid-cols-2 gap-3"><label class="text-sm font-semibold">English name<input name="label" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="e.g. Cardiology" /></label><label class="text-sm font-semibold">Arabic name<input name="ar" class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" dir="rtl" placeholder="مثال: القلب" /></label></div><button class="w-full rounded-xl bg-blue-700 text-white py-3.5 font-semibold hover:bg-blue-800">Create department or service ${icon('plus')}</button></div></form><div class="mt-6 pt-5 border-t border-slate-100"><h3 class="font-semibold">Department and service directory</h3><div class="grid md:grid-cols-2 xl:grid-cols-3 gap-3 mt-3">${directory}</div></div></section>`;
}
function admin() {
  const cmo = employees().filter(user => user.dept === 'CMO');
  const destinationOptions = managerDestinations(currentUser()).map(item => `<option value="${esc(item.key)}">${esc(item.label)} — ${esc(item.ar || '')}</option>`).join('');
  return `<div class="fade">${hero('Manager controls', 'Admin dashboard', 'Create organization-based accounts, see who is online, and manage how many employees are assigned to each destination.', btn('Export PDF report', 'export-pdf', 'bg-ink text-white hover:bg-slate-800', 'file-down'))}${organizationSetupPanel()}${departmentServicesPanel()}<div class="grid xl:grid-cols-[.8fr_1.2fr] gap-5"><section class="bg-white rounded-2xl border border-slate-100 shadow-soft p-5 sm:p-6"><div class="flex items-center gap-3 mb-5"><div class="h-10 w-10 rounded-xl bg-teal/10 text-teal flex items-center justify-center">${icon('user-plus')}</div><div><h2 class="font-bold">Create employee account</h2><p class="text-sm text-slate-500 mt-1">Assign the organization, place, role, and shift before the employee signs in.</p></div></div><form id="adminUserForm" class="space-y-3"><div class="grid sm:grid-cols-2 gap-3"><label class="text-sm font-semibold">Full name<input name="name" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="Employee name" /></label><label class="text-sm font-semibold">Staff ID<input name="id" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="EHA-0000" /></label></div><label class="text-sm font-semibold">Organization<select name="org" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3">${managerOrganizations().map(org => `<option value="${esc(org.name)}">${esc(org.name)}</option>`).join('')}</select></label><div class="grid sm:grid-cols-2 gap-3"><label class="text-sm font-semibold">Place / station<select name="dept" class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3">${destinationOptions}</select></label><label class="text-sm font-semibold">Role<select name="role" class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3">${ALL_ROLES.filter(role => role !== 'Manager').map(role => `<option>${role}</option>`).join('')}</select></label></div><div class="grid sm:grid-cols-2 gap-3"><label class="text-sm font-semibold">Username<input name="username" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="username" /></label><label class="text-sm font-semibold">Shift starts<input name="shift" type="time" value="08:00" class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" /></label></div><div class="grid sm:grid-cols-2 gap-3"><label class="text-sm font-semibold">Email<input name="email" type="email" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="name@eha.gov.eg" /></label><label class="text-sm font-semibold">Password<input name="password" type="password" minlength="6" required class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3" placeholder="Minimum 6 characters" /></label></div><button class="w-full rounded-xl bg-teal text-white py-3.5 font-semibold hover:bg-teal-700">Create account ${icon('arrow-right')}</button></form></section><section class="bg-white rounded-2xl border border-slate-100 shadow-soft overflow-hidden"><div class="p-5 border-b border-slate-100 flex items-start justify-between gap-3"><div><h2 class="font-bold">Organization workforce</h2><p class="text-sm text-slate-500 mt-1">${employees().length} employees across ${new Set(employees().map(user => user.dept)).size} destinations.</p></div><span class="live-badge">LIVE STATUS</span></div><div class="overflow-x-auto"><table class="w-full text-sm"><thead class="bg-mist text-slate-500"><tr><th class="text-left p-4">Employee</th><th class="text-left p-4">Place</th><th class="text-left p-4">Clinic slot</th><th class="text-left p-4">Status</th><th class="text-left p-4">Queue</th></tr></thead><tbody>${employees().map(user => `<tr class="border-t border-slate-100"><td class="p-4"><div class="font-semibold">${esc(user.name)}</div><div class="text-xs text-slate-400">${esc(user.id)} · ${esc(user.org || ORG_DEFAULT)}</div></td><td class="p-4">${esc(displayName(user.dept))}</td><td class="p-4">${user.dept === 'CMO' ? `Clinic ${user.cmoSlot || '—'}` : '—'}</td><td class="p-4"><button data-user-availability="${esc(user.id)}">${availabilityPill(user)}</button></td><td class="p-4 font-bold">${state.patients.filter(patient => patient.assignedTo === user.id && patient.status !== 'Done').length}</td></tr>`).join('')}</tbody></table></div></section></div><section class="mt-5 bg-white rounded-2xl border border-slate-100 shadow-soft p-5"><div class="flex items-center gap-3"><div class="h-10 w-10 rounded-xl bg-violet-50 text-violet-700 flex items-center justify-center">${icon('shuffle')}</div><div><h2 class="font-bold">Clinic balancing rules</h2><p class="text-sm text-slate-500 mt-1">Each new Clinic patient rotates to the next available Clinic slot. Unavailable employees receive no new patients and their queue is reassigned to available colleagues.</p></div></div><div class="grid md:grid-cols-3 gap-3 mt-5">${cmo.sort((a, b) => (a.cmoSlot || 9) - (b.cmoSlot || 9)).map(user => `<div class="rounded-2xl bg-mist p-4"><div class="text-xs text-slate-400">Clinic ${user.cmoSlot || '—'}</div><div class="font-semibold mt-1">${esc(user.name)}</div><div class="mt-2">${availabilityPill(user)}</div></div>`).join('')}</div></section></div>`;
}
function render() {
  if (!state.currentUser) return;
  if (!canAccess(page)) page = state.currentUser.role === 'Receptionist' ? 'kiosk' : 'overview';
  document.getElementById('pageKicker').textContent = pageTitle(page);
  const views = { overview, kiosk, queues, displays, sessions, reports, activity, admin };
  document.getElementById('main').innerHTML = (views[page] || overview)();
  nav();
  bindPage();
  lucide.createIcons();
}

function addAction(type, patient, extra = {}) {
  state.actions.push({ user: currentUser().name, userId: currentUser().id, dept: currentUser().dept, org: currentUser().org || ORG_DEFAULT, type, code: patient.code, time: now(), to: extra.to || patient.branch });
  patient.history = patient.history || [];
  patient.history.push({ at: now(), event: type, by: currentUser().name, destination: extra.to || patient.branch });
}
function availableWorkers(branch, org = ORG_DEFAULT) {
  return state.users.filter(user => user.dept === branch && (user.org || ORG_DEFAULT) === (org || ORG_DEFAULT) && user.role !== 'Manager' && user.availability !== 'unavailable');
}
function routePatient(patient, branch = patient.branch, skipUserId = null) {
  patient.branch = branch;
  const candidates = availableWorkers(branch, patient.org).filter(user => user.id !== skipUserId);
  if (!candidates.length) { patient.assignedTo = null; return null; }
  const sorted = candidates.sort((a, b) => (a.cmoSlot || 99) - (b.cmoSlot || 99));
  const pointer = Number(state.routing[branch] || 1);
  let chosenIndex = sorted.findIndex(user => (user.cmoSlot || 1) >= pointer);
  if (chosenIndex < 0) chosenIndex = 0;
  const chosen = sorted[chosenIndex];
  state.routing[branch] = (chosen.cmoSlot || (chosenIndex + 1)) + 1 > sorted.length ? 1 : (chosen.cmoSlot || (chosenIndex + 1)) + 1;
  patient.assignedTo = chosen.id;
  if (patient.status === 'Unassigned') patient.status = 'Waiting';
  return chosen;
}
function rebalanceUser(user) {
  const affected = state.patients.filter(patient => patient.assignedTo === user.id && patient.status !== 'Done');
  affected.forEach(patient => {
    const previous = user.name;
    patient.status = 'Waiting';
    patient.assignedTo = null;
    patient.history = patient.history || [];
    patient.history.push({ at: now(), event: 'Auto-queued', by: 'Routing engine', from: previous, destination: patient.branch });
    state.actions.push({ user: 'Routing engine', userId: 'SYSTEM', dept: patient.branch, org: patient.org || ORG_DEFAULT, type: 'Auto-queue', code: patient.code, time: now(), to: patient.branch === 'CMO' ? 'Shared Clinic queue' : patient.branch });
  });
  if (user.dept !== 'CMO') rebalanceWaiting(user.dept, user.org);
}
function rebalanceWaiting(branch, org = ORG_DEFAULT) {
  if (branch === 'CMO') return;
  state.patients.filter(patient => patient.branch === branch && (patient.org || ORG_DEFAULT) === (org || ORG_DEFAULT) && patient.status === 'Waiting' && !patient.assignedTo).forEach(patient => routePatient(patient, branch));
}
function setAvailability(user, next) {
  const unavailable = next === 'unavailable';
  user.availability = unavailable ? 'unavailable' : 'available';
  if (unavailable) rebalanceUser(user); else rebalanceWaiting(user.dept, user.org);
  save();
  shell();
  render();
  toast(`${user.name} is now ${unavailable ? 'unavailable; queue reassigned' : 'available for patients'}`);
}
function sessionToggle() {
  const user = currentUser();
  const active = activeSession(user.id);
  if (active) {
    active.end = now();
    user.availability = 'unavailable';
    rebalanceUser(user);
    toast('Session ended and your queue was reassigned.');
  } else {
    const shift = user.shift || '08:00';
    const start = now();
    const lateMinutes = latenessMinutes(start, shift);
    state.sessions.push({ userId: user.id, user: user.name, dept: user.dept, org: user.org, start, end: null, shift, lateMinutes });
    user.availability = 'available';
    rebalanceWaiting(user.dept);
    toast(lateMinutes ? `Session started; recorded ${lateMinutes} minutes late.` : 'Session started on time.');
  }
  save(); shell(); render();
}
function issueTicket(service) {
  let code = Number(state.nextCode);
  if (!Number.isFinite(code)) code = 1;
  code = Math.min(999, Math.max(1, Math.floor(code)));
  const usedToday = new Set(state.patients.filter(patient => isToday(patient.created) && patient.status !== 'Done').map(patient => Number(patient.code)));
  let attempts = 0;
  while (usedToday.has(code) && attempts < 999) {
    code = code === 999 ? 1 : code + 1;
    attempts += 1;
  }
  state.nextCode = code === 999 ? 1 : code + 1;
  const patient = { code, service, branch: service, org: currentUser().org || ORG_DEFAULT, status: 'Waiting', late: false, created: now(), assignedTo: null, history: [{ at: now(), event: 'Issued', by: currentUser().name, destination: service }] };
  const assigned = service === 'CMO' ? null : routePatient(patient, service);
  state.patients.push(patient);
  state.lastTicket = patient;
  state.actions.push({ user: currentUser().name, userId: currentUser().id, dept: currentUser().dept, org: currentUser().org || ORG_DEFAULT, type: 'Issue', code, time: now(), to: service });
  save();
  showTicketModal(patient, assigned);
}
function showKioskTicketSuccess(patient) {
  const item = destination(patient.service);
  const main = document.getElementById('main');
  if (!main) return;
  main.innerHTML = `<div class="kiosk-success-screen min-h-[calc(100vh-4rem)] flex items-center justify-center p-5 sm:p-8"><div class="w-full max-w-2xl text-center"><div class="flex justify-end mb-5"><button data-action="kiosk-exit" class="rounded-xl bg-white border border-slate-200 text-ink px-4 py-2.5 font-semibold hover:border-teal">Exit full screen ${icon('minimize')}</button></div><div class="bg-white rounded-[2rem] border border-emerald-100 shadow-lift p-8 sm:p-12"><div class="mx-auto h-20 w-20 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">${icon('check', 'h-10 w-10')}</div><p class="text-emerald-700 font-bold tracking-[.18em] uppercase text-sm mt-7">Ticket issued successfully</p><h1 class="text-5xl sm:text-7xl font-black text-ink mt-4">#${patient.code}</h1><p class="text-xl sm:text-2xl font-bold text-ink mt-5">${item.label} · ${item.ar}</p><p class="text-slate-500 mt-3">Your ticket has been printed. Please keep it and follow the display.</p><div class="kiosk-countdown-wrap mt-9"><div id="kioskCountdown" class="kiosk-countdown">3</div><div class="text-sm font-semibold text-slate-500 mt-3">Returning for the next patient in <span id="kioskCountdownText">3</span> seconds</div></div></div></div></div>`;
  bindPage();
  lucide.createIcons();
  let remaining = 3;
  kioskCountdownTimer = setInterval(() => {
    remaining -= 1;
    const number = document.getElementById('kioskCountdown');
    const text = document.getElementById('kioskCountdownText');
    if (number) number.textContent = String(Math.max(remaining, 0));
    if (text) text.textContent = String(Math.max(remaining, 0));
    if (remaining <= 0) {
      clearInterval(kioskCountdownTimer);
      kioskCountdownTimer = null;
      render();
      setTimeout(() => printTicket(patient), 120);
    }
  }, 1000);
}
function showTicketModal(patient, assigned) {
  if (kioskFullscreen) return showKioskTicketSuccess(patient);
  const item = destination(patient.service);
  const modal = document.createElement('div');
  modal.id = 'ticketModal';
  modal.className = 'fixed inset-0 z-[80] flex items-center justify-center p-4 modal-backdrop';
  modal.innerHTML = `<div class="bg-white rounded-3xl shadow-lift max-w-md w-full overflow-hidden"><div class="bg-ink text-white p-6 text-center"><div class="text-teal-300 text-sm font-semibold">${item.label} · ${item.ar}</div><div class="ticket-number ticket-number-lg mx-auto mt-5">${patient.code}</div><div class="mt-4">${statusPill(patient.status)}</div></div><div class="p-6"><div class="rounded-2xl bg-mist p-4 text-sm text-slate-600"><div class="flex justify-between gap-3"><span>Assigned employee</span><b class="text-ink">${assigned ? esc(assigned.name) : patient.branch === 'CMO' ? 'Shared Clinic queue' : 'Waiting for an available employee'}</b></div><div class="flex justify-between gap-3 mt-3"><span>Queue position</span><b class="text-ink">${state.patients.filter(p => p.branch === patient.branch && (p.org || ORG_DEFAULT) === (patient.org || ORG_DEFAULT) && p.status === 'Waiting').length}</b></div></div><p class="text-center text-sm text-slate-500 mt-5">Please keep this unique code and follow the live display for ${item.label}.</p><div class="flex gap-2 mt-6">${btn('Print ticket', 'modal-print', 'flex-1 bg-teal text-white hover:bg-teal-700', 'printer')}${btn('Close', 'close-modal', 'flex-1 bg-white text-ink border border-slate-200 hover:border-teal')}</div></div></div>`;
  document.body.appendChild(modal);
  modal.querySelector('[data-action="close-modal"]').onclick = () => modal.remove();
  modal.querySelector('[data-action="modal-print"]').onclick = () => printTicket(patient);
  lucide.createIcons();
}
function printTicket(patient = state.lastTicket) {
  if (!patient) return;
  const item = destination(patient.service);
  const popup = window.open('', '_blank', 'width=500,height=700');
  if (!popup) return toast('Allow pop-ups to print the patient ticket.', 'error');
  popup.document.write(`<html><head><title>PFC Ticket #${patient.code}</title><style>body{font-family:Arial,sans-serif;padding:36px;text-align:center;color:#10233f}h1{font-size:16px;margin:0;color:#0f766e}p{color:#667085}.code{font-size:92px;font-weight:800;letter-spacing:4px;margin:36px 0}.line{border-top:1px dashed #cbd5e1;margin:24px 0;padding-top:18px}</style></head><body><h1>Egypt Healthcare Authority · PFC</h1><p>${esc(item.label)} · ${esc(item.ar)}</p><div class="code">${patient.code}</div><div class="line">Please wait for your number on the ${esc(item.label)} display.</div><p>Issued ${fmt(patient.created)}</p><script>window.print()<\/script></body></html>`);
  popup.document.close();
}
function callNext() {
  const user = currentUser();
  if (user.availability === 'unavailable') return toast('Set yourself available before calling a patient.', 'error');
  if (activeSession(user.id) === undefined) sessionToggle();
  const waiting = (user.dept === 'CMO'
    ? state.patients.filter(patient => patient.branch === 'CMO' && (patient.org || ORG_DEFAULT) === (user.org || ORG_DEFAULT) && patient.status === 'Waiting' && !patient.assignedTo)
    : state.patients.filter(patient => patient.assignedTo === user.id && patient.status === 'Waiting'))
    .sort((a, b) => Number(a.late) - Number(b.late) || new Date(a.created) - new Date(b.created));
  const patient = waiting[0];
  if (!patient) return toast(user.dept === 'CMO' ? 'No waiting patient is available in the shared Clinic queue.' : 'No waiting patient is assigned to your station.', 'error');
  const previous = state.patients.find(item => item.assignedTo === user.id && item.status === 'Serving');
  if (previous) { previous.status = 'Waiting'; if (user.dept === 'CMO') previous.assignedTo = null; }
  patient.assignedTo = user.id;
  patient.status = 'Serving';
  patient.history.push({ at: now(), event: 'Called', by: user.name, destination: patient.branch });
  state.actions.push({ user: user.name, userId: user.id, dept: user.dept, type: 'Call', code: patient.code, time: now(), to: patient.branch });
  save(); render(); toast(`Ticket #${patient.code} is now serving.`);
}
function processPatient(type, code) {
  const patient = patientByCode(code);
  if (!patient) return toast('Patient ticket was not found.', 'error');
  if (patient.assignedTo && patient.assignedTo !== currentUser().id && currentUser().role !== 'Manager') return toast('This patient is assigned to another employee.', 'error');
  if (type === 'done') { patient.status = 'Done'; patient.late = false; addAction('Done', patient); toast(`Ticket #${code} marked done.`); }
  else if (type === 'late') { patient.late = true; patient.status = 'Waiting'; if (patient.branch === 'CMO') patient.assignedTo = null; addAction('Late', patient); toast(`Ticket #${code} marked late and moved behind on-time patients.`); }
  else if (type === 'transfer') openTransferModal(patient);
  save();
  if (type !== 'transfer') render();
}
function openTransferModal(patient) {
  const modal = document.createElement('div');
  modal.id = 'transferModal';
  modal.className = 'fixed inset-0 z-[80] flex items-center justify-center p-4 modal-backdrop';
  modal.innerHTML = `<div class="bg-white rounded-3xl shadow-lift max-w-md w-full p-6"><div class="flex items-start justify-between gap-4"><div><p class="text-teal font-semibold text-sm">Transfer patient</p><h2 class="text-2xl font-bold mt-1">Ticket #${patient.code}</h2><p class="text-sm text-slate-500 mt-2">Choose the next destination. The unique code will be preserved.</p></div><button data-action="close-modal" class="text-slate-400">${icon('x')}</button></div><label class="block text-sm font-semibold mt-6">Destination<select id="transferDestination" class="mt-2 w-full rounded-xl border border-slate-200 px-3 py-3">${DESTINATIONS.filter(item => item.key !== patient.branch && item.key !== 'Reception').map(item => `<option value="${item.key}">${item.label} — ${item.ar}</option>`).join('')}</select></label><div class="flex gap-2 mt-6">${btn('Transfer ticket', 'confirm-transfer', 'flex-1 bg-teal text-white hover:bg-teal-700', 'arrow-right-left')}${btn('Cancel', 'close-modal', 'flex-1 bg-white text-ink border border-slate-200 hover:border-teal')}</div></div>`;
  document.body.appendChild(modal);
  modal.querySelectorAll('[data-action="close-modal"]').forEach(button => button.onclick = () => modal.remove());
  modal.querySelector('[data-action="confirm-transfer"]').onclick = () => {
    const to = document.getElementById('transferDestination').value;
    const from = patient.branch;
    patient.branch = to; patient.service = to; patient.status = 'Waiting'; patient.late = false; patient.assignedTo = null; patient.org = patient.org || currentUser().org || ORG_DEFAULT;
    const assigned = to === 'CMO' ? null : routePatient(patient, to);
    patient.history.push({ at: now(), event: 'Transfer', by: currentUser().name, from, destination: to });
    state.actions.push({ user: currentUser().name, userId: currentUser().id, dept: currentUser().dept, type: 'Transfer', code: patient.code, time: now(), from, to });
    save(); modal.remove(); render(); toast(`Ticket #${patient.code} transferred to ${destination(to).label}${assigned ? ` · ${assigned.name}` : ''}.`);
  };
  lucide.createIcons();
}
function exportPDF() {
  const rows = reportRows();
  const popup = window.open('', '_blank', 'width=1100,height=800');
  if (!popup) return toast('Allow pop-ups to export the PDF report.', 'error');
  const htmlRows = rows.map(row => `<tr><td>${esc(row.user.name)}<br><small>${esc(row.user.id)} · ${esc(row.user.role)}</small></td><td>${esc(row.user.org || ORG_DEFAULT)}<br><small>${esc(displayName(row.user.dept))}</small></td><td>${row.active ? fmt(row.active.start) : row.records[0] ? fmt(row.records[0].start) : '—'}</td><td>${row.active ? 'Active' : row.records[0]?.end ? fmt(row.records[0].end) : '—'}</td><td>${row.minutes} min</td><td>${row.served}</td></tr>`).join('');
  popup.document.write(`<html><head><title>PFC Employee Attendance Report</title><style>body{font-family:Arial,sans-serif;padding:34px;color:#10233f}h1{margin:0 0 6px}p{color:#667085}.summary{display:flex;gap:14px;margin:22px 0}.summary div{border:1px solid #dbe4ec;border-radius:10px;padding:12px 16px;min-width:150px}.summary b{font-size:22px;display:block;margin-top:5px}table{border-collapse:collapse;width:100%;margin-top:20px}th,td{border:1px solid #dbe4ec;padding:10px;text-align:left;vertical-align:top}th{background:#eef4f7}small{color:#667085}</style></head><body><h1>PFC Employee Attendance & Service Report</h1><p>Egypt Healthcare Authority · ${esc(currentUser().globalAdmin ? 'All organizations' : (currentUser().org || ORG_DEFAULT))} · ${reportPeriod === 'week' ? 'This week' : 'This month'} · Generated ${new Date().toLocaleString()}</p><div class="summary"><div>Employees<b>${employees().length}</b></div><div>Served today<b>${scopedServedToday()}</b></div><div>Lateness<b>${rows.reduce((sum, row) => sum + row.minutes, 0)} min</b></div></div><table><thead><tr><th>Employee</th><th>Organization / place</th><th>Started</th><th>Ended</th><th>Lateness</th><th>Served today</th></tr></thead><tbody>${htmlRows}</tbody></table><script>window.print()<\/script></body></html>`);
  popup.document.close();
}
function bindPage() {
  const organizationForm = document.getElementById('organizationForm');
  if (organizationForm) organizationForm.onsubmit = event => { event.preventDefault(); createOrganization(new FormData(organizationForm)); };
  const serviceForm = document.getElementById('serviceForm');
  if (serviceForm) serviceForm.onsubmit = event => { event.preventDefault(); createDepartmentService(new FormData(serviceForm)); };
  const form = document.getElementById('adminUserForm');
  if (form) form.onsubmit = event => { event.preventDefault(); createAdminUser(new FormData(form)); };
  const queueSearch = document.getElementById('queueSearch');
  if (queueSearch) queueSearch.oninput = () => { const query = queueSearch.value.toLowerCase(); document.querySelectorAll('.patient-row').forEach(row => row.style.display = row.dataset.search.includes(query) ? 'flex' : 'none'); };
  const reportPeriodSelect = document.getElementById('reportPeriod');
  if (reportPeriodSelect) reportPeriodSelect.onchange = () => { reportPeriod = reportPeriodSelect.value; render(); };
  const reportFilter = document.getElementById('reportFilter');
  if (reportFilter) reportFilter.oninput = () => { const query = reportFilter.value.toLowerCase(); document.querySelectorAll('.report-row').forEach(row => row.style.display = row.dataset.search.includes(query) ? 'table-row' : 'none'); };
  const activityFilter = document.getElementById('activityFilter');
  if (activityFilter) activityFilter.oninput = () => { const query = activityFilter.value.toLowerCase(); document.querySelectorAll('.activity-row').forEach(row => row.style.display = row.dataset.search.includes(query) ? 'table-row' : 'none'); };
  document.querySelectorAll('[data-service]').forEach(el => el.addEventListener('click', () => issueTicket(el.dataset.service)));
  document.querySelectorAll('[data-display-mode]').forEach(el => el.addEventListener('click', () => { displayMode = el.dataset.displayMode; render(); }));
  document.querySelectorAll('[data-user-availability]').forEach(el => el.addEventListener('click', () => { const user = userById(el.dataset.userAvailability); if (user) setAvailability(user, user.availability === 'unavailable' ? 'available' : 'unavailable'); }));
  document.querySelectorAll('[data-patient-view]').forEach(el => el.addEventListener('click', () => { const patient = patientByCode(el.dataset.patientView); if (patient) openPatientDetails(patient); }));
  document.querySelectorAll('[data-action]').forEach(el => el.addEventListener('click', () => handleAction(el.dataset.action)));
}
function handleAction(action) {
  if (action === 'go-kiosk') page = 'kiosk';
  else if (action === 'go-queues') page = 'queues';
  else if (action === 'go-displays') { if (!canAccess('displays')) { toast('Live Displays are available to managers only.', 'error'); return; } page = 'displays'; }
  else if (action === 'go-reports') page = 'reports';
  else if (action === 'refresh') { render(); return; }
  else if (action === 'next-patient') { callNext(); return; }
  else if (action === 'session-toggle') { sessionToggle(); return; }
  else if (action === 'availability-toggle') { const user = currentUser(); setAvailability(user, user.availability === 'unavailable' ? 'available' : 'unavailable'); return; }
  else if (action === 'export-pdf') { exportPDF(); return; }
  else if (action === 'print-ticket') { printTicket(); return; }
  else if (action === 'kiosk-enter') { kioskFullscreen = true; shell(); }
  else if (action === 'kiosk-exit') { if (kioskCountdownTimer) { clearInterval(kioskCountdownTimer); kioskCountdownTimer = null; } kioskFullscreen = false; shell(); }
  else if (/^patient-(done|late|transfer)-\d+$/.test(action)) { const [, type, code] = action.match(/^patient-(done|late|transfer)-(\d+)$/); processPatient(type, Number(code)); return; }
  else return;
  render();
}
function openPatientDetails(patient) {
  const assigned = userById(patient.assignedTo);
  const modal = document.createElement('div');
  modal.className = 'fixed inset-0 z-[80] flex items-center justify-center p-4 modal-backdrop';
  modal.innerHTML = `<div class="bg-white rounded-3xl shadow-lift max-w-lg w-full p-6"><div class="flex items-start justify-between gap-4"><div><p class="text-teal font-semibold text-sm">Patient journey</p><h2 class="text-2xl font-bold mt-1">Ticket #${patient.code}</h2></div><button data-action="close-modal" class="text-slate-400">${icon('x')}</button></div><div class="grid sm:grid-cols-3 gap-3 mt-6"><div class="rounded-xl bg-mist p-3"><div class="text-xs text-slate-400">Destination</div><b class="block mt-1">${esc(patient.branch)}</b></div><div class="rounded-xl bg-mist p-3"><div class="text-xs text-slate-400">Status</div><div class="mt-1">${statusPill(patient.status)}</div></div><div class="rounded-xl bg-mist p-3"><div class="text-xs text-slate-400">Employee</div><b class="block mt-1 text-sm">${assigned ? esc(assigned.name) : 'Unassigned'}</b></div></div><div class="mt-6 space-y-3">${(patient.history || []).slice().reverse().map(item => `<div class="flex gap-3 text-sm"><div class="h-2 w-2 mt-1.5 rounded-full bg-teal shrink-0"></div><div><b>${esc(item.event)}</b><span class="text-slate-500"> · ${esc(item.by)}</span><div class="text-xs text-slate-400 mt-1">${fmt(item.at)}</div></div></div>`).join('')}</div><button data-action="close-modal" class="w-full mt-6 rounded-xl bg-ink text-white py-3 font-semibold">Close</button></div>`;
  document.body.appendChild(modal);
  modal.querySelectorAll('[data-action="close-modal"]').forEach(button => button.onclick = () => modal.remove());
  lucide.createIcons();
}
function createDepartmentService(formData) {
  const fields = Object.fromEntries(formData.entries());
  const org = organizationByName(fields.org);
  const label = String(fields.label || '').trim();
  const arabic = String(fields.ar || '').trim();
  const requestedKey = String(fields.key || '').trim();
  if (!org || !label) return toast('Choose an organization and enter a department or service name.', 'error');
  org.services = org.services || [];
  if ((org.departments || []).some(key => key.toLowerCase() === label.toLowerCase()) || org.services.some(service => service.label.toLowerCase() === label.toLowerCase())) return toast('This department or service already exists in the selected organization.', 'error');
  const slug = (requestedKey || label).replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_+|_+$/g, '').toUpperCase() || 'SERVICE';
  const key = `CUSTOM_${org.id}_${slug}_${Date.now().toString().slice(-6)}`;
  org.services.push({ key, label, ar: arabic, icon: fields.kind === 'Department' ? 'building-2' : 'sparkles', tone: fields.kind === 'Department' ? 'blue' : 'violet', kind: fields.kind || 'Service', organization: org.name });
  state.routing[key] = 1;
  save(); render(); toast(`${fields.kind || 'Service'} “${label}” created for ${org.name}.`);
}
function createOrganization(formData) {
  const fields = Object.fromEntries(formData.entries());
  const departments = formData.getAll('departments');
  const name = String(fields.name || '').trim();
  const managerName = String(fields.managerName || '').trim();
  const managerId = String(fields.managerId || '').trim();
  const managerUsername = String(fields.managerUsername || '').trim();
  if (!name || !managerName || !managerId || !managerUsername || !departments.length) return toast('Enter the organization, manager, and at least one department.', 'error');
  if (organizations().some(org => org.name.toLowerCase() === name.toLowerCase())) return toast('This hospital or health unit already exists.', 'error');
  if (state.users.some(existing => existing.username === managerUsername || existing.id === managerId)) return toast('Manager username or staff ID already exists.', 'error');
  const organization = { id: `ORG-${String(organizations().length + 1).padStart(3, '0')}`, name, type: fields.type || 'Health unit', location: String(fields.location || '').trim(), departments, createdAt: now() };
  const manager = { name: managerName, id: managerId, dept: 'Administration', org: name, email: String(fields.managerEmail || '').trim(), username: managerUsername, password: String(fields.managerPassword || ''), role: 'Manager', shift: '08:00', availability: 'available', globalAdmin: false };
  state.organizations.push(organization);
  state.users.push(manager);
  departments.forEach(dept => { if (!state.routing[dept]) state.routing[dept] = 1; });
  save(); render(); toast(`${organization.type} and manager account created successfully.`);
}
function createAdminUser(formData) {
  const user = Object.fromEntries(formData.entries());
  if (state.users.some(existing => existing.username === user.username || existing.id === user.id)) return toast('Username or staff ID already exists.', 'error');
  const created = { ...user, role: user.role, availability: 'unavailable', org: user.org || ORG_DEFAULT, cmoSlot: user.dept === 'CMO' ? state.users.filter(item => item.dept === 'CMO').length + 1 : undefined };
  state.users.push(created);
  save(); render(); toast(`${created.name} account created and set unavailable until they start a session.`);
}
function closeSidebar() { document.getElementById('sidebar')?.classList.add('-translate-x-full'); }

document.getElementById('loginForm').onsubmit = event => {
  event.preventDefault();
  const username = document.getElementById('loginUser').value.trim();
  const password = document.getElementById('loginPass').value;
  const user = state.users.find(item => (item.username === username || item.id === username) && item.password === password);
  if (!user) return toast('Invalid username or password.', 'error');
  state.currentUser = user;
  save();
  page = user.setup ? 'kiosk' : (user.role !== 'Manager' && user.role !== 'Receptionist' && !activeSession(user.id) ? 'sessions' : 'overview');
  shell(); render();
};
document.getElementById('signupForm').onsubmit = event => {
  event.preventDefault();
  const fields = ['suName', 'suId', 'suOrg', 'suDept', 'suRole', 'suShift', 'suEmail', 'suUser', 'suPass'];
  const values = Object.fromEntries(fields.map(id => [id, document.getElementById(id).value.trim()]));
  if (state.users.some(user => user.username === values.suUser || user.id === values.suId)) return toast('Username or staff ID already exists.', 'error');
  const user = { name: values.suName, id: values.suId, org: values.suOrg, dept: values.suDept, role: values.suRole, shift: values.suShift || '08:00', email: values.suEmail, username: values.suUser, password: values.suPass, availability: 'unavailable' };
  if (user.dept === 'CMO') user.cmoSlot = state.users.filter(item => item.dept === 'CMO').length + 1;
  state.users.push(user); state.currentUser = user; save(); page = user.role === 'Receptionist' ? 'kiosk' : 'sessions'; shell(); render(); toast('Account created. Start a session when you are ready.');
};
document.getElementById('showSignup').onclick = () => { document.getElementById('loginForm').classList.add('hidden'); document.getElementById('signupForm').classList.remove('hidden'); document.getElementById('authTitle').textContent = 'Create your account'; document.getElementById('authSubtitle').textContent = 'Choose your organization and station before you start serving.'; };
document.getElementById('showLogin').onclick = () => { document.getElementById('signupForm').classList.add('hidden'); document.getElementById('loginForm').classList.remove('hidden'); document.getElementById('authTitle').textContent = 'Welcome back'; document.getElementById('authSubtitle').textContent = 'Sign in to manage your station and queues.'; };
document.getElementById('logoutBtn').onclick = () => { state.currentUser = null; save(); location.reload(); };
document.getElementById('headerAvailability').onclick = () => { const user = currentUser(); setAvailability(user, user.availability === 'unavailable' ? 'available' : 'unavailable'); };
document.getElementById('openSide').onclick = () => document.getElementById('sidebar').classList.remove('-translate-x-full');
document.getElementById('closeSide').onclick = closeSidebar;

if (state.currentUser) { shell(); render(); } else { lucide.createIcons(); }
