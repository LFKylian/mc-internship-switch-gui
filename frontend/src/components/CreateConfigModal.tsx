import { useState } from 'react';

interface Props {
    availableProfiles: Record<string, string>;
    onSubmit: (profileId: string, name: string) => void;
    onClose: () => void;
}

export function CreateConfigModal({ availableProfiles, onSubmit, onClose }: Props) {
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [selectedProfile, setSelectedProfile] = useState(Object.keys(availableProfiles)[0] || '');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!name.trim()) {
            setError('Le nom de la configuration est obligatoire.');
            return;
        }
        onSubmit(selectedProfile, name.trim());
    };

    return (
        <div className="panel panel-compact">
            <div className='panel-header'>
                <h2>Nouvelle Configuration</h2>
            </div>
            <form className='stacked-form' onSubmit={handleSubmit}>
                <select className='input' value={selectedProfile} onChange={(e) => setSelectedProfile(e.target.value)}>
                    {Object.entries(availableProfiles).map(([id, label]) => (
                        <option key={id} value={id}>{label}</option>
                    ))}
                </select>

                <input
                    type="text"
                    placeholder="Nom de la configuration"
                    value={name}
                    onChange={(e) => { setName(e.target.value); setError(''); }}
                    autoFocus
                    className="input"
                />
                {error && <span className="field-error">{error}</span>}

                <div className="form-actions">
                    <button className="btn btn-ghost" type="button" onClick={onClose}>Annuler</button>
                    <button type="submit" className="btn btn-primary">Créer</button>
                </div>
            </form>
        </div>
    );
}