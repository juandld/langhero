import { Client, Account, ID } from 'appwrite';
import { env as publicEnv } from '$env/dynamic/public';
import { writable } from 'svelte/store';

export type AuthUser = {
  id: string;
  email: string;
  name?: string | null;
};

const AUTH_JWT_KEY = 'APPWRITE_JWT';

let client: Client | null = null;
let account: Account | null = null;

export const authUser = writable<AuthUser | null>(null);

function getConfig() {
  const endpoint = (publicEnv?.PUBLIC_APPWRITE_ENDPOINT || '').trim();
  const projectId = (publicEnv?.PUBLIC_APPWRITE_PROJECT_ID || '').trim();
  return { endpoint, projectId };
}

function getRedirectUrl() {
  const explicit = (publicEnv?.PUBLIC_APPWRITE_MAGIC_LINK_URL || '').trim();
  if (explicit) return explicit;
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/login`;
  }
  return '';
}

export function isAppwriteConfigured(): boolean {
  const { endpoint, projectId } = getConfig();
  return Boolean(endpoint && projectId);
}

function getAccount(): Account {
  if (account) return account;
  const { endpoint, projectId } = getConfig();
  if (!endpoint || !projectId) {
    throw new Error('Appwrite not configured');
  }
  client = new Client();
  client.setEndpoint(endpoint).setProject(projectId);
  account = new Account(client);
  return account;
}

export function getAuthToken(): string | null {
  try {
    if (typeof window === 'undefined') return null;
    return window.localStorage.getItem(AUTH_JWT_KEY);
  } catch {
    return null;
  }
}

function setAuthToken(token: string | null) {
  try {
    if (typeof window === 'undefined') return;
    if (token) {
      window.localStorage.setItem(AUTH_JWT_KEY, token);
    } else {
      window.localStorage.removeItem(AUTH_JWT_KEY);
    }
  } catch {}
}

export async function requestMagicLink(email: string) {
  const cleaned = (email || '').trim().toLowerCase();
  if (!cleaned) throw new Error('missing_email');
  const accountClient = getAccount();
  const userId = ID.unique();
  const redirect = getRedirectUrl();
  await accountClient.createMagicURLSession(userId, cleaned, redirect);
  return { userId, email: cleaned };
}

export async function completeMagicLink(userId: string, secret: string) {
  const accountClient = getAccount();
  await accountClient.updateMagicURLSession(userId, secret);
  const user = await accountClient.get();
  const jwt = await accountClient.createJWT();
  const profile: AuthUser = {
    id: user.$id,
    email: user.email,
    name: user.name || null,
  };
  setAuthToken(jwt.jwt || '');
  authUser.set(profile);
  return profile;
}

export async function hydrateAuth() {
  if (!isAppwriteConfigured()) return;
  try {
    const accountClient = getAccount();
    const user = await accountClient.get();
    const jwt = await accountClient.createJWT();
    const profile: AuthUser = {
      id: user.$id,
      email: user.email,
      name: user.name || null,
    };
    setAuthToken(jwt.jwt || '');
    authUser.set(profile);
  } catch {
    authUser.set(null);
  }
}

export async function logout() {
  try {
    if (isAppwriteConfigured()) {
      const accountClient = getAccount();
      await accountClient.deleteSession('current');
    }
  } catch {}
  setAuthToken(null);
  authUser.set(null);
}
