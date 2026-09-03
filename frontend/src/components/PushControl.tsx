import { useSwitchStore } from '../store/useSwitchStore';


export function PushControl() {
    const configId = useSwitchStore((s) => s.configId);
    const configName = useSwitchStore((s) => s.configName);
    const saveStatus = useSwitchStore((s) => s.saveStatus);
    const isModalOpen = useSwitchStore((s) => s.isSshModalOpen);

    const setIsSshModalOpen = useSwitchStore((s) => s.setIsSshModalOpen);
    const saveCurrentConfiguration = useSwitchStore((s) => s.saveCurrentConfiguration);

    const handlePush = async () => {
        const result = await saveCurrentConfiguration(configName);
        if (result.ok) setIsSshModalOpen(true);
    };

    const isNew = configId === null;

    if (isNew || isModalOpen) {
        return (
            <div></div>
        );
    }

    return (
        <button
            className="btn btn-primary" 
            disabled={saveStatus.saving}
            onClick={handlePush}
        >
            {saveStatus.saving ? 'Enregistrement…' : 'Déploiement'}
        </button>
    );
}
