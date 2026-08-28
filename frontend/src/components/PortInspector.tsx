import { useEffect, useState } from 'react';
import type { PortMode } from '../types/api';
import { useSwitchStore, vlanColor } from '../store/useSwitchStore';

export function PortInspector() {
  const selectedPortIds = useSwitchStore((s) => s.selectedPortIds);
  const vlans = useSwitchStore((s) => s.vlans);
  const ports = useSwitchStore((s) => s.ports);
  const applyToSelection = useSwitchStore((s) => s.applyToSelection);
  const setPortEnabled = useSwitchStore((s) => s.setPortEnabled);
  const setPortDescription = useSwitchStore((s) => s.setPortDescription);
  const removeTaggedVlan = useSwitchStore((s) => s.removeTaggedVlan);

  const [mode, setMode] = useState<PortMode>('access');
  const [nativeVlan, setNativeVlan] = useState<number>(1);
  const [taggedVlans, setTaggedVlans] = useState<number[]>([]);
  const [description, setDescription] = useState('');

  const vlanList = Object.values(vlans).sort((a, b) => a.id - b.id);
  const isSingleSelection = selectedPortIds.length === 1;
  const firstSelected = selectedPortIds[0] ? ports[selectedPortIds[0]] : undefined;

  // Reprend la config du premier port sélectionné comme point de départ du formulaire.
  useEffect(() => {
    if (firstSelected) {
      setMode(firstSelected.mode);
      setNativeVlan(firstSelected.native_vlan);
      setTaggedVlans(firstSelected.tagged_vlans);
      setDescription(firstSelected.description ?? '');
    }
  }, [selectedPortIds.join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  if (selectedPortIds.length === 0) {
    return (
      <div className="panel">
        <div className="panel-header">
          <h2>Configuration du port</h2>
        </div>
        <p className="muted empty-hint">Sélectionnez un ou plusieurs ports sur le schéma pour les configurer.</p>
      </div>
    );
  }

  const toggleTagged = (vlanId: number) => {
    setTaggedVlans((prev) => (prev.includes(vlanId) ? prev.filter((v) => v !== vlanId) : [...prev, vlanId]));
  };

  const apply = () => {
    applyToSelection(mode, nativeVlan, taggedVlans);
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Configuration du port</h2>
        <p className="muted">{selectedPortIds.length} port(s) sélectionné(s) : {selectedPortIds.join(', ')}</p>
      </div>

      <div className="field-group">
        <label className="field-label">Mode</label>
        <div className="segmented">
          <button className={mode === 'access' ? 'segmented-btn active' : 'segmented-btn'} onClick={() => setMode('access')}>
            Access
          </button>
          <button className={mode === 'trunk' ? 'segmented-btn active' : 'segmented-btn'} onClick={() => setMode('trunk')}>
            Trunk
          </button>
        </div>
      </div>

      <div className="field-group">
        <label className="field-label">{mode === 'access' ? 'VLAN' : 'VLAN natif (untagged)'}</label>
        <select className="input" value={nativeVlan} onChange={(e) => setNativeVlan(Number(e.target.value))}>
          <option value={1}>1 (défaut)</option>
          {vlanList.map((v) => (
            <option key={v.id} value={v.id}>
              {v.id} — {v.name}
            </option>
          ))}
        </select>
      </div>

      {mode === 'trunk' && (
        <div className="field-group">
          <label className="field-label">VLANs tagués</label>
          {vlanList.length === 0 && <p className="muted">Créez d'abord un VLAN.</p>}
          <div className="tag-list">
            {vlanList
              .filter((v) => v.id !== nativeVlan)
              .map((v) => (
                <label key={v.id} className="tag-checkbox">
                  <input type="checkbox" checked={taggedVlans.includes(v.id)} onChange={() => toggleTagged(v.id)} />
                  {v.id} — {v.name}
                </label>
              ))}
          </div>
        </div>
      )}

      <button className="btn btn-primary btn-block" onClick={apply}>
        Appliquer à la sélection
      </button>

      {isSingleSelection && firstSelected && (
        <div className="port-detail">
          <button
            className="btn btn-ghost btn-block"
            onClick={() => setPortEnabled(firstSelected.id, !firstSelected.enabled)}
          >
            {firstSelected.enabled ? 'Désactiver le port (shutdown)' : 'Activer le port (no shutdown)'}
          </button>

          <div className="field-group">
            <label className="field-label">Description du port</label>
            <input
              type="text"
              className="input"
              placeholder="ex. Uplink salle serveur"
              value={description}
              maxLength={64}
              onChange={(e) => setDescription(e.target.value)}
              onBlur={() => setPortDescription(firstSelected.id, description)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
              }}
            />
          </div>

          {firstSelected.mode === 'trunk' && firstSelected.tagged_vlans.length > 0 && (
            <div className="field-group">
              <label className="field-label">VLANs tagués sur ce port</label>
              <div className="tag-chip-list">
                {firstSelected.tagged_vlans
                  .slice()
                  .sort((a, b) => a - b)
                  .map((vlanId) => (
                    <span key={vlanId} className="tag-chip" style={{ borderColor: vlanColor(vlanId) }}>
                      {vlanId} — {vlans[vlanId]?.name ?? '?'}
                      <button
                        className="tag-chip-remove"
                        onClick={() => removeTaggedVlan(firstSelected.id, vlanId)}
                        aria-label={`Retirer le VLAN ${vlanId} de ce port`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
