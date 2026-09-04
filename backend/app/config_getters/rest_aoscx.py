import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from app.config_getters.base import ConfigGetter
from app.domain.get import RestAosCxDeviceInfo


class RestAosCxConfigGetter(ConfigGetter):
    """
    Implémentation de ConfigGetter pour la récupération de configuration via API REST ArubaOS-CX.
    Implémente les principes GRASP :
    - Expert : connaît les détails de l'API REST ArubaOS-CX
    - Creator : crée la configuration à partir des données du switch
    
    Note : L'API REST d'ArubaOS-CX utilise une authentification basée sur des sessions
    avec des cookies, pas HTTP Basic Auth. Le flux est :
    1. POST /rest/v1/login pour obtenir un cookie de session
    2. GET /rest/v1/system/configuration?config=running pour récupérer la config
    3. POST /rest/v1/logout pour fermer la session
    """
    
    def can_get(self, device_info: RestAosCxDeviceInfo) -> bool:
        """
        Vérifie si le switch supporte la récupération via REST API.
        Pour ArubaOS-CX, on vérifie que la méthode est rest_aoscx.
        """
        return device_info.method == "rest_aoscx"
    
    def _create_session(self, base_url: str, username: str, password: str, verify_ssl: bool) -> requests.Session:
        """
        Crée une session authentifiée avec l'API REST ArubaOS-CX.
        Retourne une session avec cookie de session valide.
        
        Note: ArubaOS-CX REST API v10.04+ utilise:
        - POST /rest/v10.04/login-sessions pour créer une session
        - Le body doit être au format x-www-form-urlencoded avec user=username&password=password
        """
        session = requests.Session()
        
        # Configuration du retry pour la résilience
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[401, 405, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # En-têtes pour l'API REST ArubaOS-CX
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # URL de login - essayer plusieurs versions de l'API
        login_urls = [
            f"{base_url}/rest/v10.04/login-sessions",
            f"{base_url}/rest/v1/login-sessions",
            f"{base_url}/rest/v1/login",
        ]
        
        for login_url in login_urls:
            try:
                # Corps de la requête de login au format x-www-form-urlencoded
                login_data = f"user={username}&password={password}"
                
                response = session.post(
                    login_url,
                    data=login_data,
                    headers=headers,
                    verify=verify_ssl,
                    timeout=30
                )
                
                # ArubaOS-CX retourne 201 Created pour une connexion réussie
                if response.status_code in [200, 201]:
                    return session
                    
            except requests.exceptions.Timeout:
                raise Exception("Timeout lors de la connexion au switch")
            except requests.exceptions.ConnectionError as e:
                raise Exception(f"Impossible de se connecter au switch: {str(e)}")
        
        # Si aucune URL n'a fonctionné
        raise Exception(f"Échec de l'authentification sur toutes les URLs de login")
    
    def get_config(self, device_info: RestAosCxDeviceInfo) -> str:
        """
        Récupère la configuration complète du switch via l'API REST ArubaOS-CX.
        """
        # Construction de l'URL de base
        protocol = "https" if device_info.use_ssl else "http"
        base_url = f"{protocol}://{device_info.host}:{device_info.port}"
        
        # Extraction des identifiants
        username = device_info.username
        password = device_info.password.get_secret_value()
        verify_ssl = device_info.use_ssl
        
        session = None
        try:
            # 1. Création de la session et authentification
            session = self._create_session(base_url, username, password, verify_ssl)
            
            # 2. Récupération de la configuration (running-config)
            # Essayer plusieurs endpoints selon la version de l'API
            config_urls = [
                f"{base_url}/rest/v10.04/system/configuration?config=running",
                f"{base_url}/rest/v1/system/configuration?config=running",
                f"{base_url}/rest/v10.04/system?method=display&cmd=show+running-config",
                f"{base_url}/rest/v1/system?method=display&cmd=show+running-config",
            ]
            
            for config_url in config_urls:
                try:
                    response = session.get(
                        config_url,
                        verify=verify_ssl,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # ArubaOS-CX retourne la configuration dans différents champs selon la version
                        if isinstance(data, dict):
                            # Format standard : {"configuration": "..."}
                            if 'configuration' in data:
                                return data['configuration']
                            # Format alternatif : {"output": "..."}
                            elif 'output' in data:
                                return data['output']
                            # Format avec liste de commandes
                            elif 'commands' in data:
                                return '\n'.join(data['commands'])
                            # Format avec message
                            elif 'message' in data:
                                return data['message']
                            # Retourne tout le JSON si aucun champ connu
                            else:
                                return str(data)
                        else:
                            return str(data)
                        
                except requests.exceptions.Timeout:
                    continue
                except Exception:
                    continue
            
            # Si aucun endpoint n'a fonctionné
            raise Exception("Aucun endpoint de configuration valide trouvé")
                
        except requests.exceptions.Timeout:
            raise Exception("Timeout lors de la récupération de la configuration")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Impossible de se connecter au switch: {str(e)}")
        except Exception as e:
            raise Exception(f"Erreur lors de la récupération de la configuration: {str(e)}")
        finally:
            # 3. Fermeture de la session (logout)
            if session is not None:
                try:
                    # Essayer plusieurs URLs de logout
                    logout_urls = [
                        f"{base_url}/rest/v10.04/login-sessions/logout",
                        f"{base_url}/rest/v1/login-sessions/logout",
                        f"{base_url}/rest/v1/logout",
                    ]
                    for logout_url in logout_urls:
                        try:
                            session.post(logout_url, verify=verify_ssl, timeout=5)
                            break
                        except Exception:
                            continue
                except Exception:
                    # On ignore les erreurs lors du logout
                    pass
                session.close()
