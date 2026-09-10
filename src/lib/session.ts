const COOKIE_NAME = "stellar_demo_session";
const DEV_SECRET = "stellar-local-development-session-key";

function base64url(bytes: Uint8Array) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

function decodeBase64url(value: string) {
  const padded = value.replaceAll("-", "+").replaceAll("_", "/") + "===".slice((value.length + 3) % 4);
  const binary = atob(padded);
  return Uint8Array.from(binary, character => character.charCodeAt(0));
}

function secret() {
  const configured = process.env.STELLAR_SESSION_SECRET;
  if (configured) return configured;
  if (process.env.NODE_ENV === "production") throw new Error("STELLAR_SESSION_SECRET is required in production.");
  return DEV_SECRET;
}

async function key() {
  return crypto.subtle.importKey("raw", new TextEncoder().encode(secret()), {name:"HMAC",hash:"SHA-256"}, false, ["sign","verify"]);
}

export async function createSession(subject = "admin") {
  const payload = base64url(new TextEncoder().encode(JSON.stringify({sub:subject,exp:Math.floor(Date.now()/1000)+8*60*60})));
  const signature = base64url(new Uint8Array(await crypto.subtle.sign("HMAC", await key(), new TextEncoder().encode(payload))));
  return `${payload}.${signature}`;
}

export async function verifySession(value?: string) {
  if (!value) return false;
  const [payload,signature,...extra] = value.split(".");
  if (!payload || !signature || extra.length) return false;
  try {
    const valid = await crypto.subtle.verify("HMAC", await key(), decodeBase64url(signature), new TextEncoder().encode(payload));
    if (!valid) return false;
    const data = JSON.parse(new TextDecoder().decode(decodeBase64url(payload))) as {sub?:string;exp?:number};
    return Boolean(data.sub && data.exp && data.exp > Math.floor(Date.now()/1000));
  } catch {
    return false;
  }
}

export { COOKIE_NAME };
