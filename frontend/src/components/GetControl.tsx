import { useSwitchStore } from '../store/useSwitchStore';


export function GetControl() {
    const configId = useSwitchStore((s) => s.configId);
    const getStatus = useSwitchStore((s) => s.getStatus);
    const isGetModalOpen = useSwitchStore((s) => s.isGetModalOpen);

    const setIsGetModalOpen = useSwitchStore((s) => s.setIsGetModalOpen);

    const handleGet = async () => {
        setIsGetModalOpen(true);
    };

    const isNew = configId === null;

    if (isNew || isGetModalOpen) {
        return (
            <div></div>
        );
    }

    return (
        <button
            className="btn btn-secondary" 
            disabled={getStatus.getting}
            onClick={handleGet}
        >
            {getStatus.getting ? 'Récupération…' : 'Récupérer'}
        </button>
    );
}
