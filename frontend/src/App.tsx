import { useEffect, useState } from 'react';
import { VlanPanel } from './components/VlanPanel';
import { UsersPanel } from './components/UsersPanel';
import { SwitchPanel } from './components/SwitchPanel';
import { CliTerminal } from './components/CliTerminal';
import { GroupsPanel } from './components/GroupsPanel';
import { SaveControl } from './components/SaveControl';
import { useSwitchStore } from './store/useSwitchStore';
import { ProfileBadge } from './components/ProfileBadge';
import { PortInspector } from './components/PortInspector';
import { UndoRedoControls } from './components/UndoRedoControls';
import { CreateConfigModal } from './components/CreateConfigModal';
import { ConfigurationsRail } from './components/ConfigurationsRail';

export default function App() {
  const init = useSwitchStore((s) => s.init);
  
  // Statuts de chargement
  const status = useSwitchStore((s) => s.status);
  const saveStatus = useSwitchStore((s) => s.saveStatus);
  const pushStatus = useSwitchStore((s) => s.pushStatus);
  const getStatus = useSwitchStore((s) => s.getStatus);

  const profile = useSwitchStore((s) => s.profile);
  const configId = useSwitchStore((s) => s.configId);
  const availableProfiles = useSwitchStore((s) => s.availableProfiles);
  const savedConfigurations = useSwitchStore((s) => s.savedConfigurations);

  const startNewConfiguration = useSwitchStore((s) => s.startNewConfiguration);
  const saveCurrentConfiguration = useSwitchStore((s) => s.saveCurrentConfiguration);

  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);

  // Variable dérivée : Vrai si n'importe quelle opération est en cours
  const isLoading =
    status.loading ||
    saveStatus.saving ||
    pushStatus.pushing ||
    getStatus.getting;

  useEffect(() => {
    void init();
  }, [init]);

  function isConfigSelected(): boolean {
    return savedConfigurations.findIndex((s) => s.id && s.id === configId) !== -1;
  }

  // Message explicatif dynamique selon l'action en cours
  const getLoadingMessage = () => {
    if (saveStatus.saving) return 'Sauvegarde en cours…';
    if (pushStatus.pushing) return 'Envoi de la configuration vers le switch…';
    if (getStatus.getting) return 'Récupération de la configuration du switch…';
    return 'Chargement en cours…';
  };

  return (
    <div className="app-shell">
      {/* Overlay de chargement global */}
      {isLoading && (
        <div className="global-loading-overlay" aria-busy="true" aria-live="polite">
          <div className="loading-card">
            <span className="spinner" />
            <p>{getLoadingMessage()}</p>
          </div>
        </div>
      )}

      <header className="app-header">
        <div className="brand">
          <span className="brand-mark" />
          <div>
            <h1>Switch Config GUI</h1>
            <p className="muted">Configuration graphique — by lef-kyks</p>
          </div>
        </div>
        <div className="header-actions">
          <ProfileBadge />
          <UndoRedoControls />
          <SaveControl creating={creating} />
        </div>
      </header>

      {status.loading && !profile && <p className="loading-hint">Chargement du profil switch…</p>}
      {status.error && !profile && <p className="field-error">{status.error}</p>}

      {profile && (
        <div className="app-body">
          <ConfigurationsRail creating={creating} setCreating={setCreating} />

          <main className="app-left">
            {creating ? (
              <div className="config-grid-1">
                <CreateConfigModal
                  availableProfiles={availableProfiles}
                  onSubmit={async (id: string, name: string) => {
                    await startNewConfiguration(id);
                    const result = await saveCurrentConfiguration(name);
                    if (result.ok) {
                      setCreating(false);
                    } else {
                      setError(result.error ?? '');
                    }
                  }}
                  onClose={() => setCreating(false)}
                />
                {error && <span className="field-error">{error}</span>}
              </div>
            ) : isConfigSelected() ? (
              <>
                <SwitchPanel />
                <div className="config-grid">
                  <VlanPanel />
                  <PortInspector />
                  <UsersPanel />
                  <GroupsPanel />
                </div>
              </>
            ) : (
              <></>
            )}
          </main>

          {!creating && isConfigSelected() && (
            <aside className="app-right">
              <CliTerminal />
            </aside>
          )}
        </div>
      )}
    </div>
  );
}