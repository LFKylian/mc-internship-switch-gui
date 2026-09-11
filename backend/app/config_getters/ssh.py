from netmiko import ConnectHandler
from netmiko import NetmikoTimeoutException, NetmikoAuthenticationException

from app.config_getters.base import ConfigGetter
from app.config_getters.parsers.aoscx import AosCxConfigParser
from app.config_getters.parsers.base import ConfigParser
from app.domain.get import SSHGetDeviceInfo, BaseGetDeviceInfo
from app.domain.models import SwitchState


class SSHConfigGetter(ConfigGetter):
    """
    Implémentation de ConfigGetter pour la récupération via SSH.
    Utilise Netmiko pour se connecter et exécuter des commandes.
    Implémente les principes GRASP :
    - Expert : connaît comment utiliser Netmiko pour récupérer la config
    - Creator : crée le SwitchState via un parseur
    - Low Coupling : délègue le parsing à un ConfigParser
    """
    
    def __init__(self, parser: ConfigParser):
        """
        Initialise le getter avec un parseur spécifique.
        Permet d'injecter différents parseurs selon le type de switch.
        """
        self.parser = parser
    
    def can_get(self, device_info: BaseGetDeviceInfo) -> bool:
        """
        Vérifie si ce getter peut gérer cette méthode de connexion.
        """
        return device_info.method == "ssh"
    
    def get_config(self, device_info: SSHGetDeviceInfo) -> SwitchState:
        """
        Récupère la configuration via SSH et la parse en SwitchState.
        """
        # Vérification du type
        if not isinstance(device_info, SSHGetDeviceInfo):
            raise ValueError("device_info doit être de type SSHGetDeviceInfo")
        
        # Conversion pour Netmiko
        netmiko_args = device_info.to_netmiko_dict()
        
        try:
            with ConnectHandler(**netmiko_args) as net_connect:
                # Exécuter la commande pour récupérer la configuration
                # Utiliser la commande spécifique si définie, sinon la commande par défaut
                command = device_info.show_running_config_cmd
                
                # Netmiko ajoute automatiquement 'enable' mode pour certaines commandes
                output = net_connect.send_command(command)
                
                # Vérifier que le parseur peut gérer cette configuration
                if not self.parser.can_parse(output):
                    raise ValueError(f"Le parseur {self.parser.__class__.__name__} ne peut pas parser cette configuration")
                
                # Parser la configuration
                return self.parser.parse(output)
                
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
            raise Exception(f"Erreur de connexion SSH: {str(e)}")
        except Exception as e:
            raise Exception(f"Erreur lors de la récupération de la configuration: {str(e)}")


# Instance concrète pour ArubaOS-CX
# Utilise le parseur AosCxConfigParser
AosCxSSHConfigGetter = SSHConfigGetter(AosCxConfigParser())
