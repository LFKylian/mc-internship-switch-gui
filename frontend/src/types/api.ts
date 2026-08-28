// Miroir des modèles Pydantic (backend/app/domain/models.py et switch_profiles/base.py).
// Les noms de champs snake_case sont conservés à l'identique pour éviter toute
// couche de mapping — le JSON échangé avec l'API est utilisé tel quel.

export type PortMode = 'access' | 'trunk';
export type PortMedium = 'rj45' | 'sfp+';

export interface PortLayout {
  x: number;
  y: number;
}

export interface PortDefinition {
  id: string;
  index: number;
  medium: PortMedium;
  layout: PortLayout;
}

export interface SwitchProfile {
  vendor_os: string;
  model: string;
  ports: PortDefinition[];
  requires_no_routing: boolean;
  max_vlan_id: number;
  reserved_vlan_ids: number[];
}

export interface Vlan {
  id: number;
  name: string;
  description?: string | null;
}

export interface Port {
  id: string;
  enabled: boolean;
  mode: PortMode;
  native_vlan: number;
  tagged_vlans: number[];
  description?: string | null;
}

export interface CommandRule {
  seq: number;
  action: 'permit' | 'deny';
  command_pattern: string;
  comment?: string | null;
}

export const BUILTIN_GROUPS = ['administrators', 'operators', 'auditors'] as const;
export type BuiltinGroup = (typeof BUILTIN_GROUPS)[number];

export interface UserGroupApi {
  name: string;
  rules: CommandRule[];
}

export interface LocalUser {
  username: string;
  group: string;
  password_plaintext: string;
}

export interface SwitchState {
  vlans: Record<number, Vlan>;
  ports: Record<string, Port>;
  users: Record<string, LocalUser>;
  user_groups: Record<string, UserGroupApi>;
}
