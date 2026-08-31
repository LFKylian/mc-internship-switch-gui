import { useEffect } from 'react';
import { useSwitchStore } from './store/useSwitchStore';
import { SwitchPanel } from './components/SwitchPanel';
import { VlanPanel } from './components/VlanPanel';
import { PortInspector } from './components/PortInspector';
import { CliTerminal } from './components/CliTerminal';
import { ProfileBadge } from './components/ProfileBadge';
import { SaveControl } from './components/SaveControl';
import { ConfigurationsRail } from './components/ConfigurationsRail';
import { UsersPanel } from './components/UsersPanel';
import { GroupsPanel } from './components/GroupsPanel';

export default function App() {
  const init = useSwitchStore((s) => s.init);
  const status = useSwitchStore((s) => s.status);
  const profile = useSwitchStore((s) => s.profile);

  useEffect(() => {
    void init();
  }, [init]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark" />
          <div>
            <h1>Aruba Switch Builder</h1>
            <p className="muted">Configuration graphique — génération CLI ArubaOS-CX</p>
          </div>
        </div>
        <div className="header-actions">
          <ProfileBadge />
          <SaveControl />
        </div>
      </header>

      {status.loading && !profile && <p className="loading-hint">Chargement du profil switch…</p>}
      {status.error && !profile && <p className="field-error">{status.error}</p>}

      {profile && (
        <div className="app-body">
          <ConfigurationsRail />

          <main className="app-left">
            <SwitchPanel />
            <div className="config-grid">
              <VlanPanel />
              <PortInspector />
              <UsersPanel />
              <GroupsPanel />
            </div>
          </main>

          <aside className="app-right">
            <CliTerminal />
          </aside>
        </div>
      )}
    </div>
  );
}



