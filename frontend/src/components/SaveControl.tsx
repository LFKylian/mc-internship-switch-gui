import { useEffect, useState } from 'react';
import { useSwitchStore } from '../store/useSwitchStore';

export function SaveControl() {
  const configId = useSwitchStore((s) => s.configId);
  const configName = useSwitchStore((s) => s.configName);
  const saveStatus = useSwitchStore((s) => s.saveStatus);
  const saveCurrentConfiguration = useSwitchStore((s) => s.saveCurrentConfiguration);
  const deleteSavedConfiguration = useSwitchStore((s) => s.deleteSavedConfiguration);

  const [editingName, setEditingName] = useState(false);
  const [draftName, setDraftName] = useState(configName);

  useEffect(() => {
    setDraftName(configName);
  }, [configName]);

  const isNew = configId === null;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await saveCurrentConfiguration(draftName);
    if (result.ok) setEditingName(false);
  };

  if (editingName || isNew) {
    return (
      <form className="save-control" onSubmit={submit}>
        <input
          type="text"
          className="input"
          placeholder="Nom de la configuration"
          value={draftName}
          onChange={(e) => setDraftName(e.target.value)}
          maxLength={100}
          autoFocus={editingName}
        />
        <button type="submit" className="btn btn-primary" disabled={saveStatus.saving}>
          {saveStatus.saving ? 'Enregistrement…' : 'Enregistrer'}
        </button>
        {!isNew && (
          <button type="button" className="btn btn-ghost" onClick={() => setEditingName(false)}>
            Annuler
          </button>
        )}
      </form>
    );
  }

  return (
    <div className="save-control">
      <button
        className="btn btn-primary"
        disabled={saveStatus.saving}
        onClick={() => void saveCurrentConfiguration(configName)}
      >
        {saveStatus.saving ? 'Enregistrement…' : `Enregistrer « ${configName} »`}
      </button>
      <button type="button" className="btn btn-ghost" onClick={() => setEditingName(true)}>
        Renommer
      </button>
      {configId !== null && (
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => {
            if (window.confirm(`Voulez-vous vraiment supprimer la configuration « ${configName} » ?`)) {
              void deleteSavedConfiguration(configId);
            }
          }}
        >
          Supprimer
        </button>
      )}
      {saveStatus.error && <p className="field-error">{saveStatus.error}</p>}
    </div>
  );
}
