// Miroir des modèles Pydantic (backend/app/domain/ et switch_profiles/base.py).
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

// Miroir de backend/app/domain/configurations.py
export interface SavedConfiguration {
  id?: number;
  name: string;
  profile_id: string;
  state: SwitchState;
  created_at?: string;
  updated_at?: string;
}


export interface BaseDeviceInfo {
  method: string,
  host: string;
  username: string;
  password: string;
}

export interface SSHDeviceInfo extends BaseDeviceInfo {
  device_type: string;
  port?: number;
  secret?: string;
}

export type DeviceInfoUnion = SSHDeviceInfo | BaseDeviceInfo;

export interface PushRequest {
  state: SwitchState;
  pushing_device_info: DeviceInfoUnion;
}

// Types pour la récupération de configuration (GET)

export interface BaseGetDeviceInfo {
  method: string;
  host: string;
  username: string;
  password: string;
}

export interface RestAosCxDeviceInfo extends BaseGetDeviceInfo {
  port?: number;
  use_ssl?: boolean;
}

export type GetDeviceInfoUnion = RestAosCxDeviceInfo | BaseGetDeviceInfo;

export interface GetRequest {
  getting_device_info: GetDeviceInfoUnion;
}

export interface GetResponse {
  status: string;
  configuration: string;
}