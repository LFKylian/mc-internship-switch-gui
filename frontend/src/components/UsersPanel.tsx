import { useState } from 'react';
import { BUILTIN_GROUPS } from '../types/api';
import { useSwitchStore } from '../store/useSwitchStore';

export function UsersPanel() {
  const users = useSwitchStore((s) => s.users);
  const userGroups = useSwitchStore((s) => s.userGroups);
  const createUser = useSwitchStore((s) => s.createUser);
  const deleteUser = useSwitchStore((s) => s.deleteUser);

  const groupOptions = [...BUILTIN_GROUPS, ...Object.keys(userGroups)];

  const [username, setUsername] = useState('');
  const [group, setGroup] = useState<string>(BUILTIN_GROUPS[0]);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const result = createUser(username, group, password);
    if (!result.ok) {
      setError(result.error ?? 'Erreur inconnue');
      return;
    }
    setUsername('');
    setPassword('');
    setError(null);
  };

  const userList = Object.values(users).sort((a, b) => a.username.localeCompare(b.username));

  return (
    <div className="panel">
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
        <button type="submit" className="btn btn-primary">
          Créer l'utilisateur
        </button>
      </form>
      {error && <p className="field-error">{error}</p>}

      <ul className="user-list">
        <li className="user-row user-row-implicit">
          <span className="user-name">admin</span>
          <span className="user-group muted">administrators (implicite)</span>
        </li>
        {userList.length === 0 && <li className="muted vlan-empty">Aucun utilisateur créé pour l'instant.</li>}
        {userList.map((user) => (
          <li key={user.username} className="user-row">
            <span className="user-name">{user.username}</span>
            <span className="user-group muted">{user.group}</span>
            <button
              className="btn btn-ghost btn-icon"
              onClick={() => deleteUser(user.username)}
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
