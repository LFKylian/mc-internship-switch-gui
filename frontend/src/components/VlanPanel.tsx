import { useState } from 'react';
import { useSwitchStore, vlanColor } from '../store/useSwitchStore';

export function VlanPanel() {
  const vlans = useSwitchStore((s) => s.vlans);
  const createVlan = useSwitchStore((s) => s.createVlan);
  const deleteVlan = useSwitchStore((s) => s.deleteVlan);

  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const numericId = Number(id);
    if (!Number.isInteger(numericId)) {
      setError('Identifiant de VLAN invalide');
      return;
    }
    const result = createVlan(numericId, name);
    if (!result.ok) {
      setError(result.error ?? 'Erreur inconnue');
      return;
    }
    setId('');
    setName('');
    setError(null);
  };

  const list = Object.values(vlans).sort((a, b) => a.id - b.id);

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>VLANs</h2>
      </div>

      <form className="vlan-form" onSubmit={submit}>
        <input
          type="number"
          placeholder="ID"
          value={id}
          onChange={(e) => setId(e.target.value)}
          className="input input-id"
          min={2}
          max={4094}
        />
        <input
          type="text"
          placeholder="Nom (ex. SERVEURS)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="input input-name"
          maxLength={32}
        />
        <button type="submit" className="btn btn-primary">
          Créer
        </button>
      </form>
      {error && <p className="field-error">{error}</p>}

      <ul className="vlan-list">
        {list.length === 0 && <li className="muted vlan-empty">Aucun VLAN créé pour l'instant.</li>}
        {list.map((vlan) => (
          <li key={vlan.id} className="vlan-row">
            <span className="vlan-swatch" style={{ background: vlanColor(vlan.id) }} />
            <span className="vlan-id">{vlan.id}</span>
            <span className="vlan-name">{vlan.name}</span>
            <button className="btn btn-ghost btn-icon" onClick={() => deleteVlan(vlan.id)} aria-label={`Supprimer le VLAN ${vlan.id}`}>
              ×
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
