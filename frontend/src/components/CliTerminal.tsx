import { useState } from 'react';
import { PushControl } from './PushControl';
import { GetControl } from './GetControl';
import { SshModal } from './push_modals/SshModal';
import { GetModal } from './push_modals/GetModal';
import { useSwitchStore } from '../store/useSwitchStore';


export function CliTerminal() {
  const cli = useSwitchStore((s) => s.cli);
  const status = useSwitchStore((s) => s.status);
  const isModalOpen = useSwitchStore((s) => s.isSshModalOpen);

  const setIsModalOpen = useSwitchStore((s) => s.setIsSshModalOpen);

  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(cli);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="panel terminal-panel">
      <div className="panel-header">
        <h2>Commandes CLI</h2>
        <button className="btn btn-ghost" onClick={copy} disabled={!cli}>
          {copied ? 'Copié' : 'Copier'}
        </button>
        <GetControl />
        <PushControl />
      </div>
      {status.error && <p className="field-error">{status.error}</p>}
      <pre className="terminal">
        <code>{cli || 'configure terminal\nexit'}</code>
      </pre>
      <p className="muted terminal-note">
        Séquence complète pour atteindre l'état désiré depuis un switch en configuration usine.
      </p>

      {/* Modale d'accès SSH */}
      <SshModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
      
      {/* Modale de récupération */}
      <GetModal isOpen={useSwitchStore((s) => s.isGetModalOpen)} onClose={() => useSwitchStore.getState().setIsGetModalOpen(false)} />
    </div>
  );

