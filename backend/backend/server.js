const http = require("node:http");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const NODE_ENV = process.env.NODE_ENV || "development";
const IS_PRODUCTION = NODE_ENV === "production";
const PORT = Number(process.env.PORT || 4000);
const HOST = process.env.HOST || "0.0.0.0";
const DEFAULT_FRONTEND_ORIGINS = IS_PRODUCTION
  ? "https://dumosense.com,https://www.dumosense.com"
  : "http://localhost:3000";
const FRONTEND_ORIGINS = (process.env.FRONTEND_ORIGIN || DEFAULT_FRONTEND_ORIGINS)
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);
const DATA_FILE = process.env.DATA_FILE || path.join(process.env.HOME || __dirname, "dumosense-data", "data.json");
const SESSION_COOKIE = "dumosense_session";
const SESSION_TTL_MS = 7 * 24 * 60 * 60 * 1000;
const COOKIE_SECURE = process.env.COOKIE_SECURE === "true" || (IS_PRODUCTION && process.env.COOKIE_SECURE !== "false");
const COOKIE_SAMESITE = process.env.COOKIE_SAMESITE || (IS_PRODUCTION ? "None" : "Lax");
const authAttempts = new Map();

if (!["Lax", "Strict", "None"].includes(COOKIE_SAMESITE)) {
  throw new Error("COOKIE_SAMESITE must be Lax, Strict, or None.");
}
if (COOKIE_SAMESITE === "None" && !COOKIE_SECURE) {
  throw new Error("COOKIE_SAMESITE=None requires COOKIE_SECURE=true.");
}

const consentCategories = [
  { key: "wellbeing", label: "Wellbeing check-ins", description: "Use your check-ins to show changes over time." },
  { key: "cognitive", label: "Cognitive check-ins", description: "Use optional cognitive check-ins for personal trends." },
  { key: "connected_devices", label: "Connected devices", description: "Connect health devices when you choose to." },
];

function loadStore() {
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE, "utf8"));
  } catch {
    return { users: [], sessions: {} };
  }
}

let store = loadStore();

function saveStore() {
  fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true });
  const temporaryFile = `${DATA_FILE}.${process.pid}.tmp`;
  fs.writeFileSync(temporaryFile, JSON.stringify(store, null, 2), { mode: 0o600 });
  fs.renameSync(temporaryFile, DATA_FILE);
}

function hashPassword(password, salt = crypto.randomBytes(16).toString("hex")) {
  return { salt, hash: crypto.scryptSync(password, salt, 64).toString("hex") };
}

function passwordMatches(password, user) {
  const actual = crypto.scryptSync(password, user.password_salt, 64);
  const expected = Buffer.from(user.password_hash, "hex");
  return actual.length === expected.length && crypto.timingSafeEqual(actual, expected);
}

function publicUser(user) {
  return {
    id: user.id,
    first_name: user.first_name,
    last_name: user.last_name,
    email: user.email,
    onboarding: user.onboarding,
    profile: user.profile,
  };
}

function sendJson(res, status, payload, headers = {}) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8", ...headers });
  res.end(JSON.stringify(payload));
}

function error(res, status, detail) {
  sendJson(res, status, { detail });
}

function setSession(res, userId) {
  const token = crypto.randomBytes(32).toString("hex");
  store.sessions[token] = { user_id: userId, created_at: Date.now() };
  saveStore();
  const secure = COOKIE_SECURE ? "; Secure" : "";
  return `${SESSION_COOKIE}=${token}; HttpOnly; Path=/; SameSite=${COOKIE_SAMESITE}; Max-Age=${SESSION_TTL_MS / 1000}${secure}`;
}

function clearSession(res, token) {
  if (token) delete store.sessions[token];
  saveStore();
  const secure = COOKIE_SECURE ? "; Secure" : "";
  res.setHeader("Set-Cookie", `${SESSION_COOKIE}=; HttpOnly; Path=/; SameSite=${COOKIE_SAMESITE}; Max-Age=0${secure}`);
}

function getCookies(req) {
  return Object.fromEntries((req.headers.cookie || "").split(";").filter(Boolean).map((part) => {
    const index = part.indexOf("=");
    return [part.slice(0, index).trim(), decodeURIComponent(part.slice(index + 1).trim())];
  }));
}

function currentUser(req) {
  const session = store.sessions[getCookies(req)[SESSION_COOKIE]];
  if (!session || Date.now() - session.created_at > SESSION_TTL_MS) return null;
  return store.users.find((user) => user.id === session.user_id) || null;
}

function clientOrigin(req) {
  const origin = req.headers.origin;
  return origin && FRONTEND_ORIGINS.includes(origin) ? origin : null;
}

function isRateLimited(req) {
  const key = `${req.socket.remoteAddress || "unknown"}:${req.url}`;
  const now = Date.now();
  const recent = (authAttempts.get(key) || []).filter((timestamp) => now - timestamp < 15 * 60 * 1000);
  recent.push(now);
  authAttempts.set(key, recent);
  return recent.length > 10;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > 1024 * 1024) reject(new Error("Request body is too large"));
    });
    req.on("end", () => {
      try { resolve(body ? JSON.parse(body) : {}); }
      catch { reject(new Error("Request body must be valid JSON")); }
    });
    req.on("error", reject);
  });
}

function requireUser(req, res) {
  const user = currentUser(req);
  if (!user) { error(res, 401, "Authentication required."); return null; }
  return user;
}

function updateUser(user, values) {
  Object.assign(user, values);
  saveStore();
  return publicUser(user);
}

async function handle(req, res) {
  const origin = clientOrigin(req);
  if (origin) res.setHeader("Access-Control-Allow-Origin", origin);
  res.setHeader("Access-Control-Allow-Credentials", "true");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS");
  res.setHeader("Vary", "Origin");
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("X-Frame-Options", "DENY");
  res.setHeader("Referrer-Policy", "no-referrer");

  if (req.method === "OPTIONS") {
    if (!origin) { res.writeHead(403); res.end(); return; }
    res.writeHead(204); res.end(); return;
  }

  const url = new URL(req.url, `http://${req.headers.host}`);
  const route = url.pathname.replace(/^\/api(?:\/|$)/, "/");

  if (req.method === "GET" && route === "/health") { sendJson(res, 200, { status: "ok" }); return; }

  try {
    if (req.method === "POST" && route === "/auth/register") {
      if (isRateLimited(req)) { error(res, 429, "Too many attempts. Please try again later."); return; }
      const body = await readBody(req);
      const firstName = String(body.first_name || "").trim();
      const lastName = String(body.last_name || "").trim();
      const email = String(body.email || "").trim().toLowerCase();
      const password = String(body.password || "");
      if (!firstName || !lastName || !/^\S+@\S+\.\S+$/.test(email) || password.length < 8) {
        error(res, 400, "Please provide a valid name, email, and password of at least 8 characters."); return;
      }
      if (store.users.some((user) => user.email === email)) { error(res, 409, "An account with this email already exists."); return; }
      const passwordData = hashPassword(password);
      const user = {
        id: crypto.randomUUID(), first_name: firstName, last_name: lastName, email,
        password_salt: passwordData.salt, password_hash: passwordData.hash,
        onboarding: { privacy_accepted: false, consent_complete: false, profile_complete: false },
        profile: {}, consent: {}, created_at: new Date().toISOString(),
      };
      store.users.push(user);
      sendJson(res, 201, publicUser(user), { "Set-Cookie": setSession(res, user.id) }); return;
    }

    if (req.method === "POST" && route === "/auth/login") {
      if (isRateLimited(req)) { error(res, 429, "Too many attempts. Please try again later."); return; }
      const body = await readBody(req);
      const email = String(body.email || "").trim().toLowerCase();
      const user = store.users.find((candidate) => candidate.email === email);
      if (!user || !passwordMatches(String(body.password || ""), user)) { error(res, 401, "Email or password is incorrect."); return; }
      sendJson(res, 200, publicUser(user), { "Set-Cookie": setSession(res, user.id) }); return;
    }

    if (req.method === "POST" && route === "/auth/logout") {
      clearSession(res, getCookies(req)[SESSION_COOKIE]); sendJson(res, 200, { ok: true }); return;
    }
    if (req.method === "GET" && route === "/auth/me") {
      const user = currentUser(req);
      if (!user) { error(res, 401, "Authentication required."); return; }
      sendJson(res, 200, publicUser(user)); return;
    }

    const user = requireUser(req, res);
    if (!user) return;
    if (req.method === "GET" && route === "/demo/status") {
      sendJson(res, 200, { demo_mode: false, demo_eligible: false });
      return;
    }
    if (req.method === "GET" && route === "/home") {
      sendJson(res, 200, {
        first_name: user.first_name,
        pattern_state: "insufficient",
        progress: { understanding: 0, preparedness: 0, action: 0 },
        change: { state: "no_change" },
        insights: {
          mindguard: { state: "no_data", count: 0 },
          health_reserve: { state: "no_data", assessed: false },
        },
        next_action: {
          title: "Start your first wellbeing check-in",
          cta: "Open MindGuard",
          target: "/app/mindguard",
        },
        ring: { connected: false },
      });
      return;
    }
    if (req.method === "GET" && route === "/privacy/summary") {
      sendJson(res, 200, {
        counts: { total: 0, mindguard: 0, ring: 0, health_reserve: 0 },
        sources: [{ key: "dumosense", label: "Dumosense account", note: "Your account and onboarding choices", active: true }],
        categories: consentCategories.map((category) => ({ ...category, granted: !!user.consent[category.key] })),
      });
      return;
    }
    if (req.method === "GET" && route === "/data-history") {
      sendJson(res, 200, { entries: [] });
      return;
    }
    if (req.method === "PUT" && route === "/onboarding") {
      sendJson(res, 200, updateUser(user, { onboarding: { ...user.onboarding, ...(await readBody(req)) } })); return;
    }
    if (req.method === "GET" && route === "/profile") { sendJson(res, 200, user.profile); return; }
    if (req.method === "PUT" && route === "/profile") {
      sendJson(res, 200, updateUser(user, { profile: { ...user.profile, ...(await readBody(req)) } })); return;
    }
    if (req.method === "GET" && route === "/consent") {
      sendJson(res, 200, { categories: consentCategories.map((category) => ({ ...category, granted: !!user.consent[category.key] })) }); return;
    }
    if (req.method === "PUT" && route === "/consent") {
      const body = await readBody(req);
      sendJson(res, 200, updateUser(user, { consent: { ...user.consent, ...(body.states || {}) } })); return;
    }
    error(res, 404, "Endpoint not found.");
  } catch (requestError) {
    error(res, 400, requestError.message);
  }
}

const server = http.createServer(handle);
server.listen(PORT, HOST, () => console.log(`Dumosense backend listening on ${HOST}:${PORT}`));
server.on("error", (serverError) => {
  console.error("Backend server error:", serverError.message);
  process.exitCode = 1;
});
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}