import { useState } from 'react';
import { SSHGetDeviceInfo, GetResponse, SwitchState } from '../../types/api';
import { useSwitchStore } from '../../store/useSwitchStore';


interface Props {
    isOpen: boolean;
    onClose: () => void;
}


export function GetModal({ isOpen, onClose }: Props) {
    const getStatus = useSwitchStore((s) => s.getStatus);
    const loadParsedConfiguration = useSwitchStore((s) => s.loadParsedConfiguration);

    const [host, setHost] = useState('');
    const [username, setUsername] = useState('admin');
    const [password, setPassword] = useState('');
    const [deviceType, setDeviceType] = useState('aruba_aoscx');
    const [port, setPort] = useState('');
    const [secret, setSecret] = useState('');
    const [showRunningConfigCmd, setShowRunningConfigCmd] = useState('show running-config');

    if (!isOpen) return null;

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!window.confirm(
            "Voulez-vous récupérer la configuration depuis le switch via SSH? " +
            "Cela écrasera votre configuration actuelle."
        )) {
            return;
        }

        const parsedPort: number = port ? Number.parseInt(port, 10) : 22;
        const deviceInfo: SSHGetDeviceInfo = {
            method: "ssh",
            host,
            username,
            password,
            device_type: deviceType,
            port: Number.isNaN(parsedPort) ? 22 : parsedPort,
            secret,
            show_running_config_cmd: showRunningConfigCmd,
        };
        
        try {
            // Appel direct à l'API
            const response = await fetch('/api/get-configuration/ssh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ getting_device_info: deviceInfo }),
            });
            
            if (!response.ok) {
                const body = await response.json().catch(() => null);
                throw new Error(body?.detail ?? `Échec de la récupération de la configuration (${response.status})`);
            }
            
            const data: GetResponse = await response.json();
            
            if (data.status === 'success' && data.state) {
                // Charger la configuration parsée dans le store
                loadParsedConfiguration(data.state);
                
                // Sauvegarder automatiquement la configuration récupérée
                // avec un nom par défaut basé sur le profil et le switch
                const store = useSwitchStore.getState();
                const configName = `from_switch_${deviceInfo.host.replace(/\./g, '_')}`;
                
                // Sauvegarder sans demander de nom (on utilise le nom par défaut)
                const saveResult = await store.saveCurrentConfiguration(configName);
                
                if (saveResult.ok) {
                    alert(`Configuration récupérée et sauvegardée sous le nom: ${configName}`);
                    onClose();
                } else {
                    alert(`Configuration chargée mais non sauvegardée: ${saveResult.error}`);
                    onClose();
                }
            } else {
                throw new Error(data.error || 'Aucune configuration retournée');
            }
            
        } catch (err: any) {
            useSwitchStore.getState().setIsGetModalOpen(true); // Garder la modale ouverte
            alert(`Erreur: ${err.message}`);
        }
    };

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <h3>Récupération de la configuration via SSH</h3>
                <form className="stacked-form" onSubmit={submit}>
                    <div className="field">
                        <label>Adresse IP du Switch</label>
                        <input
                            type="text"
                            className="input"
                            value={host}
                            onChange={(e) => setHost(e.target.value)}
                            placeholder="192.168.1.1"
                            required
                        />
                    </div>
                    <div className="field">
                        <label>Nom d'utilisateur</label>
                        <input
                            type="text"
                            className="input"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>
                    <div className="field">
                        <label>Mot de passe SSH</label>
                        <input
                            type="password"
                            className="input"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <div className="field">
                        <label>Type de l'appareil</label>
                        <input
                            type="text"
                            className="input"
                            value={deviceType}
                            onChange={(e) => setDeviceType(e.target.value)}
                            placeholder="aruba_aoscx"
                            required
                        />
                    </div>
                    <div className="field">
                        <label>Port</label>
                        <input
                            type="number"
                            className="input"
                            value={port}
                            onChange={(e) => setPort(e.target.value)}
                            placeholder="(optionnel)"
                            required={false}
                        />
                    </div>
                    <div className="field">
                        <label>Mdp mode privilégié</label>
                        <input
                            type="password"
                            className="input"
                            value={secret}
                            onChange={(e) => setSecret(e.target.value)}
                            placeholder="(optionnel)"
                            required={false}
                        />
                    </div>
                    <div className="field">
                        <label>Commande show running-config</label>
                        <input
                            type="text"
                            className="input"
                            value={showRunningConfigCmd}
                            onChange={(e) => setShowRunningConfigCmd(e.target.value)}
                            placeholder="show running-config"
                            required
                        />
                    </div>

                    <div className="save-control">
                        <button type="button" className="btn btn-ghost" onClick={onClose} disabled={getStatus.getting}>
                            Annuler
                        </button>
                        <button type="submit" className="btn btn-primary" disabled={getStatus.getting}>
                            {getStatus.getting ? 'Récupération…' : 'Récupérer'}
                        </button>
                    </div>

                    {getStatus.error && <p className="field-error">{getStatus.error}</p>}
                </form>
            </div>
        </div>
    );
}
