import React, { useEffect, useState } from 'react';
import { fetchConfigurations, saveConfiguration, deleteConfiguration, SavedConfiguration } from '../api/configurations';

interface SidebarProps {
  currentProfileId: string;
  currentState: any;
  onLoadState: (state: any) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentProfileId, currentState, onLoadState }) => {
  const [configs, setConfigs] = useState<SavedConfiguration[]>([]);
  const [newConfigName, setNewConfigName] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const loadList = async () => {
    try {
      const list = await fetchConfigurations();
      setConfigs(list);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadList();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newConfigName.trim()) return;

    setIsSaving(true);
    try {
      await saveConfiguration({
        name: newConfigName.trim(),
        profile_id: currentProfileId,
        state: currentState,
      });
      setNewConfigName('');
      await loadList();
    } catch (err) {
      alert('Erreur lors de la sauvegarde');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Supprimer cette configuration ?')) return;
    try {
      await deleteConfiguration(id);
      await loadList();
    } catch (err) {
      alert('Erreur lors de la suppression');
    }
  };

  return (
    <aside className="w-64 bg-slate-900 text-slate-100 h-screen p-4 flex flex-col border-r border-slate-800">
      <h2 className="text-lg font-semibold mb-4 text-emerald-400">Configurations</h2>

      <form onSubmit={handleSave} className="flex gap-2 mb-6">
        <input
          type="text"
          placeholder="Nom de la config..."
          value={newConfigName}
          onChange={(e) => setNewConfigName(e.target.value)}
          className="flex-1 px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm text-white focus:outline-none focus:border-emerald-500"
        />
        <button
          type="submit"
          disabled={isSaving || !newConfigName.trim()}
          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded text-sm font-medium transition-colors disabled:opacity-50"
        >
          +
        </button>
      </form>

      <div className="flex-1 overflow-y-auto space-y-2">
        {configs.map((cfg) => (
          <div
            key={cfg.id}
            onClick={() => onLoadState(cfg.state)}
            className="p-3 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 rounded cursor-pointer transition-colors flex justify-between items-center group"
          >
            <div>
              <div className="text-sm font-medium text-slate-200">{cfg.name}</div>
              <div className="text-xs text-slate-400">{cfg.profile_id}</div>
            </div>
            {cfg.id && (
              <button
                onClick={(e) => handleDelete(cfg.id!, e)}
                className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-400 transition-opacity text-xs p-1"
              >
                ✕
              </button>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
};