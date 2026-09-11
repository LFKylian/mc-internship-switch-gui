import { useState } from 'react';
import { DELETION_MARK } from '../types/api';
import { useSwitchStore, vlanColor } from '../store/useSwitchStore';


export function VlanPanel() {
  const vlans = useSwitchStore((s) => s.vlans);
  const createVlan = useSwitchStore((s) => s.createVlan);
  const updateVlan = useSwitchStore((s) => s.updateVlan);
  const deleteVlan = useSwitchStore((s) => s.deleteVlan);

  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  const isEditing = editingId !== null;

  const startEdit = (vlanId: number) => {
    const vlan = vlans[vlanId];
    if (!vlan) return;
    setEditingId(vlanId);
    setId(vlanId.toString());
    setName(vlan.name);
    
    // Nettoyage des éventuels guillemets simples pour l'affichage dans l'input
    let rawDesc = vlan.description || '';
    if (rawDesc.startsWith("'") && rawDesc.endsWith("'")) {
      rawDesc = rawDesc.slice(1, -1);
    }
    setDescription(rawDesc);
    setError(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setId('');
    setName('');
    setDescription('');
    setError(null);
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const numericId = Number(id);
    
    if (!Number.isInteger(numericId)) {
      setError('Identifiant de VLAN invalide');
      return;
    }
    if (description.includes(DELETION_MARK) || description.includes("?") || description.includes('"')) {
      setError("Cractères interdits : '?' et '\"'");
      setDescription('');
      return;
    }
    
    const result = isEditing 
      ? updateVlan(numericId, name, description) 
      : createVlan(numericId, name, description);

    if (!result.ok) {
      setError(result.error ?? 'Erreur inconnue');
      return;
    }
    
    cancelEdit();
  };

  const list = Object.values(vlans).sort((a, b) => a.id - b.id);

  return (
    <div className="panel panel-compact">
      <div className="panel-header">
        <h2>VLANs</h2>
      </div>

      <form className="stacked-form" onSubmit={submit}>
        <div className="vlan-form">
          <input
            type="number"
            placeholder="ID"
            value={id}
            onChange={(e) => setId(e.target.value)}
            className="input input-id"
            min={2}
            max={4094}
            disabled={isEditing}
          />
          <input
            type="text"
            placeholder="Nom (ex. SERVEURS)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input input-name"
            maxLength={32}
          />
        </div>
        <input
          type="text"
          placeholder="Description (optionnelle)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="input"
          maxLength={64}
        />
        <div className="form-actions">
          <button type="submit" className="btn btn-primary">
            {isEditing ? 'Enregistrer' : 'Créer'}
          </button>
          {isEditing && (
            <button type="button" className="btn btn-ghost" onClick={cancelEdit}>
              Annuler
            </button>
          )}
        </div>
      </form>
      {error && <p className="field-error">{error}</p>}

      <ul className="vlan-list">
        {list.length === 0 && <li className="muted vlan-empty">Aucun VLAN créé pour l'instant.</li>}
        {list.map((vlan) => (
          <li 
            key={vlan.id} 
            className={`vlan-row vlan-row-editable${editingId === vlan.id ? ' active' : ''}`}
            onClick={() => startEdit(vlan.id)}
          >
            <span className="vlan-swatch" style={{ background: vlanColor(vlan.id) }} />
            <span className="vlan-id">{vlan.id}</span>
            <span className="vlan-name">{vlan.name}</span>
            <button 
              className="btn btn-ghost btn-icon" 
              onClick={(e) => {
                e.stopPropagation();
                if (editingId === vlan.id) cancelEdit();
                deleteVlan(vlan.id);
              }} 
              aria-label={`Supprimer le VLAN ${vlan.id}`}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}