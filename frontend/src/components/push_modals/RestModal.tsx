import { useState } from 'react';
import { RestAosCxDeviceInfo } from '../../types/api';
import { useSwitchStore } from '../../store/useSwitchStore';


interface Props {
    isOpen: boolean;
    onClose: () => void;
}


export function RestModal({ isOpen, onClose }: Props) {
    const getConfiguration = useSwitchStore((s) => s.getConfiguration);
    const getStatus = useSwitchStore((s) => s.getStatus);

    const [host, setHost] = useState('');
    const [username, setUsername] = useState('admin');
    const [password, setPassword] = useState('');
    const [port, setPort] = useState('443');
    const [useSsl, setUseSsl] = useState(true);

    if (!isOpen) return null;

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!window.confirm(
            "Voulez-vous récupérer la configuration depuis le switch via API REST? Assurez-vous que cette fonctionnalité est activée sur le switch."
        )) {
            return;
        }

        const parsedPort: number = port ? Number.parseInt(port, 10) : 443;
        const deviceInfo: RestAosCxDeviceInfo = {
            method: "rest_aoscx",
            host,
            username,
            password,
            port: Number.isNaN(parsedPort) ? 443 : parsedPort,
            use_ssl: useSsl,
        };
        const success = await getConfiguration(deviceInfo.method, deviceInfo);
        if (success) {
            window.alert(`Configuration récupérée avec succès:\n\n${getStatus.configuration}`);
            onClose();
        }
    };

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <h3>Récupération de la configuration via API REST</h3>
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
                        <label>Mot de passe</label>
                        <input
                            type="password"
                            className="input"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
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
                            placeholder="443"
                            required={false}
                        />
                    </div>
                    <div className="field">
                        <label>
                            <input
                                type="checkbox"
                                checked={useSsl}
                                onChange={(e) => setUseSsl(e.target.checked)}
                            />
                            Utiliser SSL (HTTPS)
                        </label>
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
