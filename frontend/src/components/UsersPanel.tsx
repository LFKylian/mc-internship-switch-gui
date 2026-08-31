import { useEffect, useState } from 'react';
import { BUILTIN_GROUPS } from '../types/api';
import { useSwitchStore } from '../store/useSwitchStore';

export function UsersPanel() {
  const users = useSwitchStore((s) => s.users);
  const userGroups = useSwitchStore((s) => s.userGroups);
  const createUser = useSwitchStore((s) => s.createUser);
  const updateUser = useSwitchStore((s) => s.updateUser);
  const deleteUser = useSwitchStore((s) => s.deleteUser);

  const groupOptions = [...BUILTIN_GROUPS, ...Object.keys(userGroups)];

  const [editingUsername, setEditingUsername] = useState<string | null>(null);
  const [username, setUsername] = useState('');
  const [group, setGroup] = useState<string>(BUILTIN_GROUPS[0]);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEditing = editingUsername !== null;

  const startEdit = (name: string) => {
    const user = users[name];
    if (!user) return;
    setEditingUsername(name);
    setUsername(name);
    setGroup(user.group);
    setPassword(user.password_plaintext);
    setError(null);
  };

  const cancelEdit = () => {
    setEditingUsername(null);
    setUsername('');
    setPassword('');
    setError(null);
  };

  // Si le groupe en cours d'édition disparaît (suppression), on retombe sur une option valide.
  useEffect(() => {
    if (!groupOptions.includes(group)) setGroup(groupOptions[0] ?? '');
  }, [groupOptions.join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const result = isEditing ? updateUser(editingUsername!, group, password) : createUser(username, group, password);
    if (!result.ok) {
      setError(result.error ?? 'Erreur inconnue');
      return;
    }
    cancelEdit();
  };

  const userList = Object.values(users).sort((a, b) => a.username.localeCompare(b.username));

  return (
    <div className="panel panel-compact">
      <div className="panel-header">
        <h2>Utilisateurs</h2>
      </div>

      <form className="stacked-form" onSubmit={submit}>
        <input
          type="text"
          placeholder="Nom d'utilisateur"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="input"
          maxLength={32}
          disabled={isEditing}
        />
        <select className="input" value={group} onChange={(e) => setGroup(e.target.value)}>
          {groupOptions.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
        <div className="password-row">
          <input
            type={showPassword ? 'text' : 'password'}
            placeholder="Mot de passe (plaintext)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input"
            maxLength={64}
          />
          <button type="button" className="btn btn-ghost" onClick={() => setShowPassword((v) => !v)}>
            {showPassword ? 'Masquer' : 'Voir'}
          </button>
        </div>
        <div className="form-actions">
          <button type="submit" className="btn btn-primary">
            {isEditing ? 'Enregistrer' : 'Créer'}
          </button>
          {isEditing && (
            <button type="button" className="btn btn-ghost" onClick={cancelEdit}>
              Annuler
            </button>
          )}
        </div>
      </form>
      {error && <p className="field-error">{error}</p>}

      <ul className="user-list list-below-form">
        <li className="user-row user-row-implicit">
          <span className="user-name">admin</span>
          <span className="user-group muted">administrators (implicite)</span>
        </li>
        {userList.length === 0 && <li className="muted list-empty">Aucun utilisateur créé.</li>}
        {userList.map((user) => (
          <li
            key={user.username}
            className={`user-row user-row-editable${editingUsername === user.username ? ' active' : ''}`}
            onClick={() => startEdit(user.username)}
          >
            <span className="user-name">{user.username}</span>
            <span className="user-group muted">{user.group}</span>
            <button
              className="btn btn-ghost btn-icon"
              onClick={(e) => {
                e.stopPropagation();
                if (editingUsername === user.username) cancelEdit();
                deleteUser(user.username);
              }}
              aria-label={`Supprimer ${user.username}`}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}