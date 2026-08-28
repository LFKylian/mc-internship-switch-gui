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

export interface SwitchState {
  vlans: Record<number, Vlan>;
  ports: Record<string, Port>;
}
