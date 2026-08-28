import { useSwitchStore } from '../store/useSwitchStore';

export function ProfileSelector() {
  const availableProfiles = useSwitchStore((s) => s.availableProfiles);
  const profileId = useSwitchStore((s) => s.profileId);
  const selectProfile = useSwitchStore((s) => s.selectProfile);
  const loading = useSwitchStore((s) => s.status.loading);

  const entries = Object.entries(availableProfiles);
  if (entries.length === 0) return null;

  return (
    <label className="profile-selector">
      <span className="field-label">Modèle de switch</span>
      <select
        className="input"
        value={profileId}
        disabled={loading}
        onChange={(e) => void selectProfile(e.target.value)}
      >
        {entries.map(([id, model]) => (
          <option key={id} value={id}>
            {model}
          </option>
        ))}
      </select>
    </label>
  );
}
