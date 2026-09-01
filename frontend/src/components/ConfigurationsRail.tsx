import { useState } from 'react';
import { useSwitchStore } from '../store/useSwitchStore';

export function ConfigurationsRail() {
  const savedConfigurations = useSwitchStore((s) => s.savedConfigurations);
  const configId = useSwitchStore((s) => s.configId);
  const availableProfiles = useSwitchStore((s) => s.availableProfiles);
  const hasUnsavedChanges = useSwitchStore((s) => s.hasUnsavedChanges);
  const loadConfiguration = useSwitchStore((s) => s.loadConfiguration);
  const deleteSavedConfiguration = useSwitchStore((s) => s.deleteSavedConfiguration);
  const startNewConfiguration = useSwitchStore((s) => s.startNewConfiguration);

  const [creating, setCreating] = useState(false);

  const profileEntries = Object.entries(availableProfiles);

  return (
    <nav className="app-rail" aria-label="Configurations sauvegardées">
      <div className="app-rail-list">
        {savedConfigurations.map((cfg) => (
          <button
            key={cfg.id}
            className={`app-rail-item${configId === cfg.id ? ' active' : ''}`}
            title={`${cfg.name} — ${cfg.profile_id}`}
            onClick={() => {
              if (hasUnsavedChanges() && !window.confirm(
                'Vous avez des modifications non sauvegardées. Voulez-vous vraiment quitter cette configuration ?'
              )) {
                return;
              }
              cfg.id !== undefined && void loadConfiguration(cfg.id);
            }}
          >
            <span className="app-rail-initial">{cfg.name.charAt(0).toUpperCase()}</span>
          </button>
        ))}
      </div>

      {creating ? (
        <div className="app-rail-new-menu">
          {profileEntries.map(([id, model]) => (
            <button
              key={id}
              className="app-rail-new-option"
              title={model}
              onClick={() => {
                if (hasUnsavedChanges() && !window.confirm(
                  'Vous avez des modifications non sauvegardées. Voulez-vous vraiment créer une nouvelle configuration ?'
                )) {
                  return;
                }
                void startNewConfiguration(id);
                setCreating(false);
              }}
            >
              {model}
            </button>
          ))}
        </div>
      ) : (
        <button className="app-rail-item app-rail-add" title="Nouvelle configuration" onClick={() => setCreating(true)}>
          +
        </button>
      )}
    </nav>
  );
}
