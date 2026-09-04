import { create } from 'zustand';
import type {
  BaseDeviceInfo,
  BaseGetDeviceInfo,
  CommandRule,
  LocalUser,
  Port,
  PortMode,
  SavedConfiguration,
  SwitchProfile,
  SwitchState,
  UserGroupApi,
  Vlan,
} from '../types/api';
import { BUILTIN_GROUPS } from '../types/api';
import {
  deleteConfiguration as apiDeleteConfiguration,
  fetchConfiguration,
  fetchConfigurations,
  fetchProfile,
  fetchProfileList,
  generateCli,
  saveConfiguration as apiSaveConfiguration,
  pushConfiguration as apiPushConfiguration,
  getConfiguration as apiGetConfiguration,
} from '../api/client';

const DEFAULT_PROFILE_ID = 'aruba-6100-48g-4sfp';
const MAX_LOCAL_USERS = 63;
const MAX_USER_GROUPS = 29;

function defaultPort(id: string): Port {
  return { id, enabled: true, mode: 'access', native_vlan: 1, tagged_vlans: [] };
}

function vlanColor(id: number): string {
  // Rotation par angle d'or : couleurs stables et bien réparties, quel que
  // soit le nombre de VLANs créés (pas de palette figée à 6 entrées).
  const hue = (id * 137.508) % 360;
  return `hsl(${hue}, 62%, 55%)`;
}

interface Status {
  loading: boolean;
  error: string | null;
}

interface SaveStatus {
  saving: boolean;
  error: string | null;
}

interface SwitchStoreState {
  profileId: string;
  availableProfiles: Record<string, string>; // id -> nom du modèle
  profile: SwitchProfile | null;
  vlans: Record<number, Vlan>;
  ports: Record<string, Port>;
  users: Record<string, LocalUser>;
  userGroups: Record<string, UserGroupApi>;
  selectedPortIds: string[];
  cli: string;
  status: Status;

  // Configuration actuellement chargée. Le profil est immuable une fois une
  // configuration démarrée : on ne le change plus via un sélecteur libre —
  // seule startNewConfiguration() peut en choisir un, et uniquement pour
  // repartir d'une configuration vierge.
  configId: number | null;
  configName: string;
  savedConfigurations: SavedConfiguration[];
  saveStatus: SaveStatus;

  // Snapshot de l'état au moment du dernier chargement/sauvegarde pour détecter les modifications non sauvegardées
  savedSnapshot: string | null;

  pushStatus: { pushing: boolean; error: string | null; output: string | null };
  isSshModalOpen: boolean;
  
  getStatus: { getting: boolean; error: string | null; configuration: string | null };
  isGetModalOpen: boolean;
  
  init: () => Promise<void>;
  startNewConfiguration: (profileId: string) => Promise<void>;
  loadConfigurationList: () => Promise<void>;
  loadConfiguration: (id: number) => Promise<void>;
  saveCurrentConfiguration: (name: string) => Promise<{ ok: boolean; error?: string }>;
  deleteSavedConfiguration: (id: number) => Promise<void>;
  hasUnsavedChanges: () => boolean;
  togglePortSelection: (portId: string, additive: boolean) => void;
  clearSelection: () => void;
  createVlan: (id: number, name: string) => { ok: boolean; error?: string };
  deleteVlan: (id: number) => void;
  applyToSelection: (mode: PortMode, nativeVlan: number, taggedVlans: number[]) => void;
  setPortEnabled: (portId: string, enabled: boolean) => void;
  setPortDescription: (portId: string, description: string) => void;
  removeTaggedVlan: (portId: string, vlanId: number) => void;
  
  createUser: (username: string, group: string, passwordPlaintext: string) => { ok: boolean; error?: string };
  updateUser: (username: string, group: string, passwordPlaintext: string) => { ok: boolean; error?: string };
  deleteUser: (username: string) => void;
  createGroup: (name: string) => { ok: boolean; error?: string };
  deleteGroup: (name: string) => void;
  addGroupRule: (groupName: string, rule: CommandRule) => { ok: boolean; error?: string };
  removeGroupRule: (groupName: string, seq: number) => void;

  pushConfiguration: (modal:string, pushingDeviceInfo: BaseDeviceInfo) => Promise<boolean>;
  setIsSshModalOpen: (open: boolean) => void;
  
  getConfiguration: (modal: string, gettingDeviceInfo: BaseGetDeviceInfo) => Promise<boolean>;
  setIsGetModalOpen: (open: boolean) => void;
}

function buildSwitchState(state: SwitchStoreState): SwitchState {
  return {
    vlans: state.vlans,
    ports: state.ports,
    users: state.users,
    user_groups: state.userGroups,
  };
}

let cliRequestSeq = 0;

async function refreshCli(get: () => SwitchStoreState, set: (partial: Partial<SwitchStoreState>) => void) {
  const seq = ++cliRequestSeq;
  const state = get();
  try {
    const cli = await generateCli(state.profileId, buildSwitchState(state));
    if (seq !== cliRequestSeq) return; // une requête plus récente a déjà été lancée entre-temps : on ignore ce résultat périmé
    set({ cli, status: { loading: false, error: null } });
  } catch (err) {
    if (seq !== cliRequestSeq) return;
    set({ status: { loading: false, error: (err as Error).message } });
  }
}

async function loadProfileData(
  profileId: string,
  set: (partial: Partial<SwitchStoreState>) => void,
  get: () => SwitchStoreState,
) {
  set({ status: { loading: true, error: null } });
  try {
    const profile = await fetchProfile(profileId);
    const ports: Record<string, Port> = {};
    profile.ports.forEach((def) => {
      ports[def.id] = defaultPort(def.id);
    });
    set({
      profileId,
      profile,
      vlans: {},
      ports,
      users: {},
      userGroups: {},
      selectedPortIds: [],
      configId: null,
      configName: '',
      status: { loading: false, error: null },
    });
    await refreshCli(get, set);
  } catch (err) {
    set({ status: { loading: false, error: (err as Error).message } });
  }
}

function validateGroupAndPassword(
  group: string,
  passwordPlaintext: string,
  userGroups: Record<string, UserGroupApi>,
): { ok: boolean; error?: string } {
  const knownGroups = new Set<string>([...BUILTIN_GROUPS, ...Object.keys(userGroups)]);
  if (!knownGroups.has(group)) return { ok: false, error: `Groupe '${group}' inconnu` };
  if (!passwordPlaintext || !/^[\x21-\x7E]+$/.test(passwordPlaintext)) {
    return { ok: false, error: 'Mot de passe invalide (caractères ASCII imprimables uniquement, sans espace)' };
  }
  return { ok: true };
}

export const useSwitchStore = create<SwitchStoreState>((set, get) => ({
  profileId: DEFAULT_PROFILE_ID,
  availableProfiles: {},
  profile: null,
  vlans: {},
  ports: {},
  users: {},
  userGroups: {},
  selectedPortIds: [],
  cli: '',
  status: { loading: true, error: null },
  configId: null,
  configName: '',
  savedConfigurations: [],
  saveStatus: { saving: false, error: null },
  savedSnapshot: null,
  pushStatus: { pushing: false, error: null, output: null },
  isSshModalOpen: false,
  
  getStatus: { getting: false, error: null, configuration: null },
  isGetModalOpen: false,
  
  init: async () => {
    try {
      const availableProfiles = await fetchProfileList();
      set({ availableProfiles });
    } catch (err) {
      set({ status: { loading: false, error: (err as Error).message } });
      return;
    }
    await loadProfileData(get().profileId, set, get);
    void get().loadConfigurationList();
  },
  
  // Point d'entrée unique pour choisir un profil : repart toujours d'une
  // configuration vierge. C'est la seule façon de changer de modèle de
  // switch — il n'existe plus de sélecteur libre une fois une configuration
  // en cours (cf. commentaire sur configId dans l'interface).
  startNewConfiguration: async (profileId) => {
    await loadProfileData(profileId, set, get);
    // Mise à jour du snapshot après chargement d'une nouvelle configuration vierge
    set({ savedSnapshot: JSON.stringify(buildSwitchState(get())) });
  },
  
  loadConfigurationList: async () => {
    try {
      const savedConfigurations = await fetchConfigurations();
      set({ savedConfigurations });
    } catch (err) {
      set({ saveStatus: { saving: false, error: (err as Error).message } });
    }
  },
  
  loadConfiguration: async (id) => {
    set({ status: { loading: true, error: null } });
    try {
      const saved = await fetchConfiguration(id);
      // Chaque configuration sauvegardée porte le profil avec lequel elle a
      // été créée (immuable) : on ne le redemande pas, on le restaure.
      if (saved.profile_id !== get().profileId) {
        await loadProfileData(saved.profile_id, set, get);
      }
      set({
        vlans: saved.state.vlans,
        ports: saved.state.ports,
        users: saved.state.users,
        userGroups: saved.state.user_groups,
        selectedPortIds: [],
        configId: saved.id ?? null,
        configName: saved.name,
        status: { loading: false, error: null },
        savedSnapshot: JSON.stringify(saved.state),
      });
      await refreshCli(get, set);
    } catch (err) {
      set({ status: { loading: false, error: (err as Error).message } });
    }
  },
  
  saveCurrentConfiguration: async (name) => {
    const trimmed = name.trim();
    if (!trimmed) return { ok: false, error: 'Nom de configuration requis' };
    
    set({ saveStatus: { saving: true, error: null } });
    try {
      const state = get();
      const saved = await apiSaveConfiguration({
        id: state.configId ?? undefined,
        name: trimmed,
        profile_id: state.profileId,
        state: buildSwitchState(state),
      });
      set({
        configId: saved.id ?? null,
        configName: saved.name,
        saveStatus: { saving: false, error: null },
        savedSnapshot: JSON.stringify(buildSwitchState(state)),
      });
      await get().loadConfigurationList();
      return { ok: true };
    } catch (err) {
      const error = (err as Error).message;
      set({ saveStatus: { saving: false, error } });
      return { ok: false, error };
    }
  },

  deleteSavedConfiguration: async (id) => {
    try {
      await apiDeleteConfiguration(id);
      if (get().configId === id) set({ configId: null, configName: '' });
      await get().loadConfigurationList();
    } catch (err) {
      set({ saveStatus: { saving: false, error: (err as Error).message } });
    }
  },
  
  hasUnsavedChanges: () => {
    const state = get();
    if (state.savedSnapshot === null) return false;
    return state.savedSnapshot !== JSON.stringify(buildSwitchState(state));
  },
  
  togglePortSelection: (portId, additive) =>
    set((state) => {
      if (!additive) return { selectedPortIds: [portId] };
      const exists = state.selectedPortIds.includes(portId);
      return {
        selectedPortIds: exists
        ? state.selectedPortIds.filter((id) => id !== portId)
        : [...state.selectedPortIds, portId],
      };
    }),
    
  clearSelection: () => set({ selectedPortIds: [] }),

  createVlan: (id, name) => {
    const { profile, vlans } = get();
    if (!profile) return { ok: false, error: 'Profil non chargé' };
    if (id < 2 || id > profile.max_vlan_id || profile.reserved_vlan_ids.includes(id)) {
      return { ok: false, error: `VLAN hors plage autorisée (2–${profile.max_vlan_id})` };
    }
    if (vlans[id]) return { ok: false, error: `Le VLAN ${id} existe déjà` };
    if (!name.trim()) return { ok: false, error: 'Nom de VLAN requis' };

    const nextVlans = { ...vlans, [id]: { id, name: name.trim() } };
    set({ vlans: nextVlans });
    void refreshCli(get, set);
    return { ok: true };
  },

  deleteVlan: (id) => {
    set((state) => {
      const vlans = { ...state.vlans };
      delete vlans[id];
      // Tout port référençant ce VLAN retombe sur l'état par défaut (access, VLAN 1)
      const ports = { ...state.ports };
      Object.values(ports).forEach((port) => {
        if (port.native_vlan === id || port.tagged_vlans.includes(id)) {
          ports[port.id] = { ...defaultPort(port.id), enabled: port.enabled, description: port.description };
        }
      });
      return { vlans, ports };
    });
    void refreshCli(get, set);
  },

  applyToSelection: (mode, nativeVlan, taggedVlans) => {
    set((state) => {
      const ports = { ...state.ports };
      state.selectedPortIds.forEach((portId) => {
        const current = ports[portId];
        if (!current) return;
        ports[portId] = {
          ...current,
          mode,
          native_vlan: nativeVlan,
          tagged_vlans: mode === 'trunk' ? taggedVlans.filter((v) => v !== nativeVlan) : [],
        };
      });
      return { ports };
    });
    void refreshCli(get, set);
  },

  setPortEnabled: (portId, enabled) => {
    set((state) => {
      const current = state.ports[portId];
      if (!current) return state;
      const ports = { ...state.ports, [portId]: { ...current, enabled } };
      return { ports };
    });
    void refreshCli(get, set);
  },

  setPortDescription: (portId, description) => {
    set((state) => {
      const current = state.ports[portId];
      if (!current) return state;
      const trimmed = description.trim();
      const ports = { ...state.ports, [portId]: { ...current, description: trimmed || undefined } };
      return { ports };
    });
    void refreshCli(get, set);
  },

  removeTaggedVlan: (portId, vlanId) => {
    set((state) => {
      const current = state.ports[portId];
      if (!current) return state;
      const ports = {
        ...state.ports,
        [portId]: { ...current, tagged_vlans: current.tagged_vlans.filter((v) => v !== vlanId) },
      };
      return { ports };
    });
    void refreshCli(get, set);
  },

  createUser: (username, group, passwordPlaintext) => {
    const { users, userGroups } = get();
    const name = username.trim();
    if (!name) return { ok: false, error: "Nom d'utilisateur requis" };
    if (name === 'admin') return { ok: false, error: "'admin' est implicite : inutile de le recréer" };
    if (users[name]) return { ok: false, error: `L'utilisateur '${name}' existe déjà` };
    if (Object.keys(users).length >= MAX_LOCAL_USERS) {
      return { ok: false, error: `Maximum ${MAX_LOCAL_USERS} utilisateurs locaux` };
    }
    const groupCheck = validateGroupAndPassword(group, passwordPlaintext, userGroups);
    if (!groupCheck.ok) return groupCheck;

    set({ users: { ...users, [name]: { username: name, group, password_plaintext: passwordPlaintext } } });
    void refreshCli(get, set);
    return { ok: true };
  },

  updateUser: (username, group, passwordPlaintext) => {
    const { users, userGroups } = get();
    const existing = users[username];
    if (!existing) return { ok: false, error: `L'utilisateur '${username}' n'existe pas` };
    const groupCheck = validateGroupAndPassword(group, passwordPlaintext, userGroups);
    if (!groupCheck.ok) return groupCheck;

    // Un utilisateur appartient à un seul groupe à la fois : cette mise à jour
    // remplace l'affectation précédente, elle ne s'y ajoute pas.
    set({ users: { ...users, [username]: { ...existing, group, password_plaintext: passwordPlaintext } } });
    void refreshCli(get, set);
    return { ok: true };
  },

  deleteUser: (username) => {
    set((state) => {
      const users = { ...state.users };
      delete users[username];
      return { users };
    });
    void refreshCli(get, set);
  },

  createGroup: (name) => {
    const { userGroups } = get();
    const trimmed = name.trim();
    if (!trimmed) return { ok: false, error: 'Nom de groupe requis' };
    if ((BUILTIN_GROUPS as readonly string[]).includes(trimmed)) {
      return { ok: false, error: `'${trimmed}' est un nom de groupe réservé` };
    }
    if (userGroups[trimmed]) return { ok: false, error: `Le groupe '${trimmed}' existe déjà` };
    if (Object.keys(userGroups).length >= MAX_USER_GROUPS) {
      return { ok: false, error: `Maximum ${MAX_USER_GROUPS} groupes définis` };
    }

    set({ userGroups: { ...userGroups, [trimmed]: { name: trimmed, rules: [] } } });
    void refreshCli(get, set);
    return { ok: true };
  },

  deleteGroup: (name) => {
    set((state) => {
      const userGroups = { ...state.userGroups };
      delete userGroups[name];
      // Les utilisateurs affectés à ce groupe perdent leur affectation : on les
      // retombe sur 'operators' plutôt que de laisser une référence invalide.
      const users = { ...state.users };
      Object.values(users).forEach((user) => {
        if (user.group === name) {
          users[user.username] = { ...user, group: 'operators' };
        }
      });
      return { userGroups, users };
    });
    void refreshCli(get, set);
  },

  addGroupRule: (groupName, rule) => {
    const { userGroups } = get();
    const group = userGroups[groupName];
    if (!group) return { ok: false, error: 'Groupe introuvable' };
    if (group.rules.some((r) => r.seq === rule.seq)) {
      return { ok: false, error: `La séquence ${rule.seq} est déjà utilisée dans ce groupe` };
    }
    if (!rule.command_pattern.trim()) return { ok: false, error: 'Motif de commande requis' };

    const rules = [...group.rules, rule].sort((a, b) => a.seq - b.seq);
    set({ userGroups: { ...userGroups, [groupName]: { ...group, rules } } });
    void refreshCli(get, set);
    return { ok: true };
  },

  removeGroupRule: (groupName, seq) => {
    set((state) => {
      const group = state.userGroups[groupName];
      if (!group) return state;
      const userGroups = {
        ...state.userGroups,
        [groupName]: { ...group, rules: group.rules.filter((r) => r.seq !== seq) },
      };
      return { userGroups };
    });
    void refreshCli(get, set);
  },

  pushConfiguration: async (modal: string, pushingDeviceInfo: BaseDeviceInfo) => {
    const state = get();

    if (!state.profileId) {
      set({ pushStatus: { pushing: false, error: 'Profil non trouvé', output: null } });
      return false;
    }

    set({ pushStatus: { pushing: true, error: null, output: null } });

    try {
      const output = await apiPushConfiguration(state.profileId, modal, {
        state: buildSwitchState(state),
        pushing_device_info: pushingDeviceInfo,
      });

      set({
        pushStatus: {
          pushing: false,
          error: null,
          output: output,
        },
      });
      return true;

    } catch (err: any) {
      set({
        pushStatus: {
          pushing: false,
          error: err.message || 'Erreur lors du déploiement',
          output: null,
        },
      });
      return false;
    }
  },

  setIsSshModalOpen: (open) => set({ isSshModalOpen: open }),

  getConfiguration: async (modal: string, gettingDeviceInfo: BaseGetDeviceInfo) => {
    set({ getStatus: { getting: true, error: null, configuration: null } });

    try {
      const response = await apiGetConfiguration(modal, {
        getting_device_info: gettingDeviceInfo,
      });

      set({
        getStatus: {
          getting: false,
          error: null,
          configuration: response.configuration,
        },
      });
      return true;

    } catch (err: any) {
      set({
        getStatus: {
          getting: false,
          error: err.message || 'Erreur lors de la récupération de la configuration',
          configuration: null,
        },
      });
      return false;
    }
  },

  setIsGetModalOpen: (open) => set({ isGetModalOpen: open }),

}));

export { vlanColor };



