import type { SwitchProfile, SwitchState } from '../types/api';

const BASE_URL = '/api';

export async function fetchProfileList(): Promise<Record<string, string>> {
  const res = await fetch(`${BASE_URL}/profiles`);
  if (!res.ok) throw new Error(`Échec du chargement de la liste des profils (${res.status})`);
  return res.json();
}

export async function fetchProfile(profileId: string): Promise<SwitchProfile> {
  const res = await fetch(`${BASE_URL}/profiles/${profileId}`);
  if (!res.ok) throw new Error(`Échec du chargement du profil (${res.status})`);
  return res.json();
}

export async function generateCli(profileId: string, state: SwitchState): Promise<string> {
  const res = await fetch(`${BASE_URL}/profiles/${profileId}/generate-cli`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(state),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Échec de la génération CLI (${res.status})`);
  }
  const data = await res.json();
  return data.cli as string;
}
