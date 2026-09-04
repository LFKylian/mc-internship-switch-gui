from typing import Optional
import requests
from requests.auth import HTTPBasicAuth
from app.config_getters.base import ConfigGetter
from app.domain.get import RestAosCxDeviceInfo


class RestAosCxConfigGetter(ConfigGetter):
    """
    Implémentation de ConfigGetter pour la récupération de configuration via API REST ArubaOS-CX.
    Implémente les principes GRASP :
    - Expert : connaît les détails de l'API REST ArubaOS-CX
    - Creator : crée la configuration à partir des données du switch
    """
    
    def can_get(self, device_info: RestAosCxDeviceInfo) -> bool:
        """
        Vérifie si le switch supporte la récupération via REST API.
        Pour ArubaOS-CX, on vérifie que la méthode est rest_aoscx.
        """
        return device_info.method == "rest_aoscx"
    
    def get_config(self, device_info: RestAosCxDeviceInfo) -> str:
        """
        Récupère la configuration complète du switch via l'API REST ArubaOS-CX.
        
        Utilise pyaoscx ou requests pour se connecter à l'API REST du switch.
        L'API REST d'ArubaOS-CX expose un endpoint pour récupérer la configuration.
        
        Note : Cette implémentation utilise requests directement car pyaoscx n'est pas
        toujours disponible. Une future amélioration pourrait utiliser pyaoscx si installé.
        """
        # Construction de l'URL de base
        protocol = "https" if device_info.use_ssl else "http"
        base_url = f"{protocol}://{device_info.host}:{device_info.port}"
        
        # Endpoint pour récupérer la configuration complète (running-config)
        config_url = f"{base_url}/rest/v10.04/system?method=display&cmd=show+running-config"
        
        # Authentification
        auth = HTTPBasicAuth(device_info.username, device_info.password.get_secret_value())
        
        # En-têtes pour accepter du JSON
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        try:
            # Requête GET pour récupérer la configuration
            response = requests.get(
                config_url,
                auth=auth,
                headers=headers,
                verify=False,  # Désactive la vérification SSL pour les switches avec certificats auto-signés
                timeout=30
            )
            
            # Vérification du statut de la réponse
            if response.status_code == 200:
                # L'API REST retourne la configuration dans un format spécifique
                # On extrait et retourne la configuration complète
                data = response.json()
                
                # ArubaOS-CX retourne la configuration dans le champ 'configuration'
                # ou directement dans le corps de la réponse
                if isinstance(data, dict) and 'configuration' in data:
                    return data['configuration']
                elif isinstance(data, dict) and 'output' in data:
                    return data['output']
                else:
                    # Si la réponse est directement la configuration
                    return str(data)
            else:
                # Gestion des erreurs
                error_msg = f"Erreur {response.status_code}: {response.text}"
                raise Exception(error_msg)
                
        except requests.exceptions.Timeout:
            raise Exception("Timeout lors de la connexion au switch via REST API")
        except requests.exceptions.ConnectionError:
            raise Exception("Impossible de se connecter au switch via REST API")
        except requests.exceptions.AuthenticationError:
            raise Exception("Erreur d'authentification REST API")
        except Exception as e:
            raise Exception(f"Erreur lors de la récupération de la configuration: {str(e)}")
