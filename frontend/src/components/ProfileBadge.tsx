import { useSwitchStore } from '../store/useSwitchStore';

export function ProfileBadge() {
  const profile = useSwitchStore((s) => s.profile);
  if (!profile) return null;

  return (
    <div className="profile-badge" title="Le modèle de switch est fixé à la création de la configuration">
      <span className="field-label">Modèle de switch</span>
      <span className="profile-badge-value">{profile.model}</span>
    </div>
  );
}
