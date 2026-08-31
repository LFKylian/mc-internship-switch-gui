export interface SavedConfiguration {
  id?: number;
  name: string;
  profile_id: string;
  state: any;
  created_at?: string;
  updated_at?: string;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchConfigurations(): Promise<SavedConfiguration[]> {
  const res = await fetch(`${API_BASE}/api/configurations`);
  if (!res.ok) throw new Error('Erreur chargement des configurations');
  return res.json();
}

export async function saveConfiguration(config: SavedConfiguration): Promise<SavedConfiguration> {
  const res = await fetch(`${API_BASE}/api/configurations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error('Erreur lors de la sauvegarde');
  return res.json();
}

export async function deleteConfiguration(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/configurations/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Erreur lors de la suppression');
}