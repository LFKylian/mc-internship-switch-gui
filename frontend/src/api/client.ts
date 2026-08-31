import type { SavedConfiguration, SwitchProfile, SwitchState } from '../types/api';

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

export async function fetchConfigurations(): Promise<SavedConfiguration[]> {
  const res = await fetch(`${BASE_URL}/configurations`);
  if (!res.ok) throw new Error(`Échec du chargement des configurations (${res.status})`);
  return res.json();
}

export async function fetchConfiguration(id: number): Promise<SavedConfiguration> {
  const res = await fetch(`${BASE_URL}/configurations/${id}`);
  if (!res.ok) throw new Error(`Échec du chargement de la configuration (${res.status})`);
  return res.json();
}

export async function saveConfiguration(config: SavedConfiguration): Promise<SavedConfiguration> {
  const res = await fetch(`${BASE_URL}/configurations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Échec de la sauvegarde (${res.status})`);
  }
  return res.json();
}

export async function deleteConfiguration(id: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/configurations/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Échec de la suppression (${res.status})`);
}



