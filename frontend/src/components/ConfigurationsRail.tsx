import { useSwitchStore } from '../store/useSwitchStore';

interface Props {
  creating: boolean;
  setCreating: (c: boolean) => void;
}

export function ConfigurationsRail({creating, setCreating}: Props) {
  const configId = useSwitchStore((s) => s.configId);
  const savedConfigurations = useSwitchStore((s) => s.savedConfigurations);

  const hasUnsavedChanges = useSwitchStore((s) => s.hasUnsavedChanges);
  const loadConfiguration = useSwitchStore((s) => s.loadConfiguration);

  return (
    <nav className="app-rail" aria-label="Configurations sauvegardées">
      {/* En-tête fixe : le bouton d'ajout reste toujours accessible en haut */}
      <div className="rail-header">
        {creating ? ( 
          <></>
        ) : (
          <button
            type="button"
            className="rail-tab-add"
            title="Nouvelle configuration"
            onClick={() => setCreating(true)}
          >
            +
          </button>
        )}
      </div>

      {/* Zone défilante des onglets */}
      <div className="rail-tabs-container">
        {savedConfigurations.map((cfg) => (
          <button
            key={cfg.id}
            type="button"
            className={`rail-tab${configId === cfg.id ? ' active' : ''}`}
            title={`${cfg.name} — ${cfg.profile_id}`}
            onClick={() => {
              if (
                hasUnsavedChanges() &&
                !window.confirm(
                  'Vous avez des modifications non sauvegardées. Voulez-vous vraiment quitter cette configuration ?'
                )
              ) {
                return;
              }
              cfg.id !== undefined && void loadConfiguration(cfg.id);
            }}
          >
            <span className="rail-tab-text">{cfg.name}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}