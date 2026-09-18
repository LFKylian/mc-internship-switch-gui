import { useSwitchStore } from '../store/useSwitchStore';
import { useTemporalStore } from '../store/useTemporalStore';
import { useUndoRedoShortcuts } from '../hooks/useUndoRedoShortcuts';

export function UndoRedoControls() {
  useUndoRedoShortcuts();

  const { undo, redo, pastStates, futureStates } = useTemporalStore((s) => ({
    undo: s.undo,
    redo: s.redo,
    pastStates: s.pastStates,
    futureStates: s.futureStates,
  }));

  const refreshCli = useSwitchStore((s) => s.refreshCliAfterZundo);

  const canUndo = pastStates.length > 0;
  const canRedo = futureStates.length > 0;

  return (
    <div className="undo-redo-controls" style={{ display: 'flex', gap: '6px' }}>
      <button
        type="button"
        className="btn btn-ghost"
        onClick={async () => {undo(); await refreshCli()}}
        disabled={!canUndo}
        title="Annuler (Ctrl+Z)"
      >
        ↩ Annuler
      </button>
      <button
        type="button"
        className="btn btn-ghost"
        onClick={async () => {redo(); await refreshCli()}}
        disabled={!canRedo}
        title="Rétablir (Ctrl+Y)"
      >
        ↪ Rétablir
      </button>
    </div>
  );
}