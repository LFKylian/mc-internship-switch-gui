import { useState } from 'react';
import type { CommandRule } from '../types/api';
import { BUILTIN_GROUPS } from '../types/api';
import { useSwitchStore } from '../store/useSwitchStore';

export function GroupsPanel() {
  const userGroups = useSwitchStore((s) => s.userGroups);
  const createGroup = useSwitchStore((s) => s.createGroup);
  const deleteGroup = useSwitchStore((s) => s.deleteGroup);
  const addGroupRule = useSwitchStore((s) => s.addGroupRule);
  const removeGroupRule = useSwitchStore((s) => s.removeGroupRule);

  const customGroups = Object.values(userGroups).sort((a, b) => a.name.localeCompare(b.name));

  const [newGroupName, setNewGroupName] = useState('');
  const [groupError, setGroupError] = useState<string | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);

  const [seq, setSeq] = useState('10');
  const [action, setAction] = useState<CommandRule['action']>('permit');
  const [pattern, setPattern] = useState('');
  const [comment, setComment] = useState('');
  const [ruleError, setRuleError] = useState<string | null>(null);

  const submitGroup = (e: React.FormEvent) => {
    e.preventDefault();
    const result = createGroup(newGroupName);
    if (!result.ok) {
      setGroupError(result.error ?? 'Erreur inconnue');
      return;
    }
    setSelectedGroup(newGroupName.trim());
    setNewGroupName('');
    setGroupError(null);
  };

  const submitRule = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGroup) return;
    const seqNum = Number(seq);
    if (!Number.isInteger(seqNum) || seqNum < 1) {
      setRuleError('Numéro de séquence invalide');
      return;
    }
    const result = addGroupRule(selectedGroup, {
      seq: seqNum,
      action,
      command_pattern: pattern,
      comment: comment.trim() || undefined,
    });
    if (!result.ok) {
      setRuleError(result.error ?? 'Erreur inconnue');
      return;
    }
    setSeq(String(seqNum + 10));
    setPattern('');
    setComment('');
    setRuleError(null);
  };

  const activeGroup = selectedGroup ? userGroups[selectedGroup] : undefined;

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Groupes</h2>
      </div>

      <div className="group-list">
        {BUILTIN_GROUPS.map((g) => (
          <span key={g} className="group-chip group-chip-builtin">
            {g}
          </span>
        ))}
        {customGroups.map((g) => (
          <button
            key={g.name}
            className={`group-chip group-chip-custom${selectedGroup === g.name ? ' active' : ''}`}
            onClick={() => setSelectedGroup(g.name)}
          >
            {g.name}
            <span
              className="group-chip-remove"
              onClick={(e) => {
                e.stopPropagation();
                if (selectedGroup === g.name) setSelectedGroup(null);
                deleteGroup(g.name);
              }}
              role="button"
              aria-label={`Supprimer le groupe ${g.name}`}
            >
              ×
            </span>
          </button>
        ))}
      </div>

      <form className="vlan-form" onSubmit={submitGroup}>
        <input
          type="text"
          placeholder="Nouveau groupe (ex. noc-readonly)"
          value={newGroupName}
          onChange={(e) => setNewGroupName(e.target.value)}
          className="input input-name"
          maxLength={32}
        />
        <button type="submit" className="btn btn-primary">
          Créer
        </button>
      </form>
      {groupError && <p className="field-error">{groupError}</p>}

      {activeGroup && (
        <div className="port-detail">
          <label className="field-label">
            Règles de "{activeGroup.name}" — évaluées par ordre croissant de séquence, la première correspondance
            l'emporte (deny implicite en fin de liste)
          </label>

          <ul className="rule-list">
            {activeGroup.rules.length === 0 && (
              <li className="muted vlan-empty">Aucune règle : ce groupe n'a aucun droit (deny implicite).</li>
            )}
            {activeGroup.rules
              .slice()
              .sort((a, b) => a.seq - b.seq)
              .map((rule) => (
                <li key={rule.seq} className="rule-row">
                  <span className="rule-seq">{rule.seq}</span>
                  <span className={rule.action === 'permit' ? 'rule-action permit' : 'rule-action deny'}>
                    {rule.action}
                  </span>
                  <code className="rule-pattern">{rule.command_pattern}</code>
                  <button
                    className="btn btn-ghost btn-icon"
                    onClick={() => removeGroupRule(activeGroup.name, rule.seq)}
                    aria-label={`Retirer la règle ${rule.seq}`}
                  >
                    ×
                  </button>
                </li>
              ))}
          </ul>

          <form className="rule-form" onSubmit={submitRule}>
            <input
              type="number"
              value={seq}
              onChange={(e) => setSeq(e.target.value)}
              className="input input-id"
              min={1}
              max={1024}
              aria-label="Séquence"
            />
            <select
              className="input rule-action-select"
              value={action}
              onChange={(e) => setAction(e.target.value as CommandRule['action'])}
            >
              <option value="permit">permit</option>
              <option value="deny">deny</option>
            </select>
            <input
              type="text"
              placeholder='Motif de commande, ex. "show .*"'
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
              className="input rule-pattern-input"
            />
            <button type="submit" className="btn btn-primary">
              Ajouter
            </button>
          </form>
          <input
            type="text"
            placeholder="Commentaire (optionnel)"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            className="input"
            maxLength={64}
          />
          {ruleError && <p className="field-error">{ruleError}</p>}
        </div>
      )}
    </div>
  );
}
