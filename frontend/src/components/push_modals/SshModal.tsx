import { useState } from 'react';
import { SSHDeviceInfo } from '../../types/api';
import { useSwitchStore } from '../../store/useSwitchStore';


interface Props {
    isOpen: boolean;
    onClose: () => void;
}


export function SshModal({ isOpen, onClose }: Props) {
    const pushConfiguration = useSwitchStore((s) => s.pushConfiguration);
    const pushStatus = useSwitchStore((s) => s.pushStatus);

    const [host, setHost] = useState('');
    const [username, setUsername] = useState('admin');
    const [password, setPassword] = useState('');
    const [deviceType, setDeviceType] = useState('');
    const [port, setPort] = useState('');
    const [secret, setSecret] = useState('');

    if (!isOpen) return null;

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!window.confirm(
            "Votre configuration va être déployer"
        )) {
            return;
        }

        const parsedPort: number = port ? Number.parseInt(port, 10) : 22;
        const deviceInfo: SSHDeviceInfo = {
            method: "ssh",
            host,
            username,
            password,
            device_type: deviceType,
            port: Number.isNaN(parsedPort) ? 22 : parsedPort,
            secret
        }
        const success = await pushConfiguration(deviceInfo.method, deviceInfo);
        if (success) {
            window.alert(`Sortie :\n\n${pushStatus.output}`);
            onClose();
        }
    };

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <h3>Déploiement SSH vers le switch</h3>
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

                    <div className="save-control">
                        <button type="button" className="btn btn-ghost" onClick={onClose} disabled={pushStatus.pushing}>
                            Annuler
                        </button>
                        <button type="submit" className="btn btn-primary" disabled={pushStatus.pushing}>
                            {pushStatus.pushing ? 'Déploiement…' : 'Déployer'}
                        </button>
                    </div>

                    {pushStatus.error && <p className="field-error">{pushStatus.error}</p>}
                </form>
            </div>
        </div>
    );
}