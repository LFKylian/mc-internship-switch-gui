import { useState } from 'react';
import { DELETION_MARK, IpAddress } from '../types/api';
import { useSwitchStore, vlanColor } from '../store/useSwitchStore';


export function VlanPanel() {
  const vlans = useSwitchStore((s) => s.vlans);
  const createVlan = useSwitchStore((s) => s.createVlan);
  const updateVlan = useSwitchStore((s) => s.updateVlan);
  const deleteVlan = useSwitchStore((s) => s.deleteVlan);

  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const [mask, setMask] = useState('');
  const [ipAddress, setIpInterface] = useState('');
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
    
    if (vlan.ip_interface) {
      setMask(vlan.ip_interface.mask);
      setIpInterface(vlan.ip_interface.ip);
    } else {
      setMask('');
      setIpInterface('');
    }
    
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
    setMask('');
    setIpInterface('');
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
      setError("Cractères interdits : ? et \"");
      setDescription('');
      return;
    }
    if (ipAddress && !mask) {
      setError("Masque manquant")
      return;
    }
    if (!ipAddress && mask) {
      setError("Adresse IP manquante")
      return;
    }
    if (ipAddress && !isValidIPv4(ipAddress)) {
      setError("Adresse IP invalide");
      return;
    }
    if (mask && !isValidMask(mask)) {
      setError("Masque invalide");
      return;
    }
    
    const vlanIpInterface: IpAddress | null = ipAddress && mask ? {ip: ipAddress, mask} : null;
    const result = isEditing 
    ? updateVlan(numericId, name, description, vlanIpInterface) 
    : createVlan(numericId, name, description, vlanIpInterface);
    
    if (!result.ok) {
      setError(result.error ?? 'Erreur inconnue');
      return;
    }
    
    cancelEdit();
  };

  const isValidIPv4 = (ip: string): boolean => {
    const parts = ip.trim().split('.');
    if (parts.length !== 4) return false;

    return parts.every((part, index) => {
      if (!/^\d+$/.test(part)) return false; // Uniquement des chiffres
      if (part.length > 1 && part.startsWith('0')) return false; // Pas de zéro en-tête (ex: 01)
      
      const num = Number(part);
      if (index === 3) {
        return num >= 1 && num <= 254; // Dernier octet hôte (1-254)
      }
      return num >= 0 && num <= 255; // Octets 0 à 2 (0-255)
    });
  };

  // Valide un masque CIDR (1 à 32)
  const isValidMask = (mask: string): boolean => {
    const num = Number(mask);
    return Number.isInteger(num) && num >= 1 && num <= 32;
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
        <div className="vlan-form">
          <input
            type="text"
            placeholder="Interface IP (optionnelle)"
            value={ipAddress}
            onChange={(e) => setIpInterface(e.target.value)}
            className="input"
          />
          <input
            type="number"
            placeholder="Masque"
            value={mask}
            onChange={(e) => setMask(e.target.value)}
            className="input input-id"
            min={1}
            max={32}
          />
        </div>
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