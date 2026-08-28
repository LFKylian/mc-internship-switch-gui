import type { PortDefinition } from '../types/api';
import { useSwitchStore, vlanColor } from '../store/useSwitchStore';

const PORT_W = 22;
const RJ45_H = 15;
const SFP_H = 12;

function portFill(portState: ReturnType<typeof useSwitchStore.getState>['ports'][string] | undefined): string {
  if (!portState) return 'var(--surface-3)';
  return vlanColor(portState.native_vlan);
}

function Jack({ def }: { def: PortDefinition }) {
  const port = useSwitchStore((s) => s.ports[def.id]);
  const selected = useSwitchStore((s) => s.selectedPortIds.includes(def.id));
  const toggle = useSwitchStore((s) => s.togglePortSelection);

  const h = def.medium === 'sfp+' ? SFP_H : RJ45_H;
  const fill = portFill(port);
  const isTrunk = port?.mode === 'trunk';
  const isUp = port?.enabled ?? true;

  return (
    <g
      transform={`translate(${def.layout.x}, ${def.layout.y})`}
      onClick={(e) => toggle(def.id, e.shiftKey || e.metaKey || e.ctrlKey)}
      className="port-jack"
      tabIndex={0}
      role="button"
      aria-label={`Port ${def.id}${port ? `, VLAN ${port.native_vlan}, ${port.mode}, ${isUp ? 'up' : 'down'}` : ''}`}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') toggle(def.id, e.shiftKey);
      }}
    >
      {def.medium === 'sfp+' ? (
        <polygon
          points={`2,${h} 0,0 ${PORT_W - 2},0 ${PORT_W},${h}`}
          fill={fill}
          stroke={selected ? 'var(--accent)' : 'var(--border-1)'}
          strokeWidth={selected ? 2 : 1}
        />
      ) : (
        <>
          <rect width={PORT_W} height={h} rx={1.5} fill={fill} stroke={selected ? 'var(--accent)' : 'var(--border-1)'} strokeWidth={selected ? 2 : 1} />
          {/* encoche évoquant le clip RJ45 */}
          <rect x={PORT_W / 2 - 3} y={-2} width={6} height={2} fill={selected ? 'var(--accent)' : 'var(--border-1)'} />
        </>
      )}
      {/* état du lien (haut-gauche) */}
      <circle cx={3.5} cy={3.5} r={2} fill={isUp ? '#109200' : 'var(--danger)'} stroke="#05070b" strokeWidth={0.6} />
      {/* mode trunk (bas-droit) */}
      {isTrunk && <circle cx={PORT_W - 4} cy={h - 4} r={2} fill="var(--accent)" stroke="#05070b" strokeWidth={0.6} />}
      <text x={PORT_W / 2} y={h + 10} className="port-label" textAnchor="middle">
        {def.index}
      </text>
    </g>
  );
}

export function SwitchPanel() {
  const profile = useSwitchStore((s) => s.profile);
  const clearSelection = useSwitchStore((s) => s.clearSelection);

  if (!profile) return null;

  const width = Math.max(...profile.ports.map((p) => p.layout.x)) + PORT_W + 24;

  return (
    <div className="panel switch-panel">
      <div className="panel-header">
        <div>
          <h2>{profile.model}</h2>
          <p className="muted">{profile.ports.length} ports · clic pour sélectionner, Maj+clic pour la sélection multiple</p>
        </div>
      </div>
      <div className="switch-faceplate-scroll">
        <svg
          viewBox={`0 0 ${width} 110`}
          className="switch-faceplate"
          onClick={(e) => {
            if (e.target === e.currentTarget) clearSelection();
          }}
        >
          {profile.ports.map((def) => (
            <Jack key={def.id} def={def} />
          ))}
        </svg>
      </div>
    </div>
  );
}
