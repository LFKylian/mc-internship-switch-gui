import re
from typing import Dict, List, Optional

from app.config_getters.parsers.base import ConfigParser
from app.domain.models import Port, PortMode, SwitchState, Vlan
from app.domain.users import LocalUser


class AosCxConfigParser(ConfigParser):
    """
    Parseur de configuration ArubaOS-CX.
    Transforme la sortie de 'show running-config' en SwitchState.
    Implémente les principes GRASP :
    - Expert : connaît le format de configuration ArubaOS-CX
    - Creator : crée le SwitchState à partir du texte brut
    """
    
    def can_parse(self, raw_config: str) -> bool:
        """
        Vérifie si le texte semble être une configuration ArubaOS-CX.
        """
        # ArubaOS-CX a des marqueurs spécifiques
        markers = [
            "! ArubaOS-CX",
            "! Software image",
            "hostname",
            "interface",
            "vlan",
        ]
        return any(marker in raw_config for marker in markers)
    
    def parse(self, raw_config: str) -> SwitchState:
        """
        Parse la configuration brute ArubaOS-CX et retourne un SwitchState.
        """
        vlans: Dict[int, Vlan] = {}
        ports: Dict[str, Port] = {}
        users: Dict[str, LocalUser] = {}
        user_groups: Dict[str, dict] = {}
        
        # Nettoyage initial
        lines = raw_config.splitlines()
        
        # État de parsing
        current_section = None
        current_vlan_id = None
        current_port_id = None
        current_user = None
        
        for line in lines:
            line = line.strip()
            
            # Ignorer les commentaires et lignes vides
            if not line or line.startswith('!') or line.startswith('#'):
                continue
            
            # Détection des sections principales
            if line.startswith('hostname'):
                current_section = 'hostname'
                continue
            
            # Section VLAN
            if line.startswith('vlan '):
                match = re.match(r'vlan\s+(\d+)', line)
                if match:
                    current_vlan_id = int(match.group(1))
                    current_section = 'vlan'
                    vlans[current_vlan_id] = Vlan(id=current_vlan_id, name="")
                continue
            
            # Nom du VLAN
            if current_section == 'vlan' and line.startswith('name '):
                match = re.match(r'name\s+"?.+?"?\s+(\S+)', line)
                if match:
                    vlan_name = match.group(1).strip('"')
                    if current_vlan_id and current_vlan_id in vlans:
                        vlans[current_vlan_id].name = vlan_name
                continue
            
            # Section Interface
            if line.startswith('interface '):
                match = re.match(r'interface\s+(\S+)', line)
                if match:
                    current_port_id = match.group(1)
                    current_section = 'interface'
                    # Initialiser le port avec des valeurs par défaut
                    ports[current_port_id] = Port(
                        id=current_port_id,
                        enabled=True,
                        mode=PortMode.ACCESS,
                        native_vlan=1,
                        tagged_vlans=[]
                    )
                continue
            
            # Fermeture de section interface
            if line == 'exit' and current_section == 'interface':
                current_section = None
                current_port_id = None
                continue
            
            # Configuration dans une interface
            if current_section == 'interface' and current_port_id:
                port = ports[current_port_id]
                
                # Mode trunk
                if 'trunk' in line.lower():
                    port.mode = PortMode.TRUNK
                
                # VLAN natif
                match = re.search(r'untagged\s+vlan\s+(\d+)', line, re.IGNORECASE)
                if match:
                    port.native_vlan = int(match.group(1))
                
                # VLANs tagués
                match = re.search(r'tagged\s+vlan\s+(\d+(?:\s+\d+)*)', line, re.IGNORECASE)
                if match:
                    vlan_ids = [int(v) for v in match.group(1).split()]
                    port.tagged_vlans = vlan_ids
                
                # Port désactivé
                if 'disable' in line.lower() or 'shutdown' in line.lower():
                    port.enabled = False
                
                # Description
                match = re.search(r'description\s+"([^"]*)"', line, re.IGNORECASE)
                if match:
                    port.description = match.group(1)
                continue
            
            # Section utilisateurs locaux
            if line.startswith('username ') and 'password' in line.lower():
                match = re.match(r'username\s+(\S+)\s+password\s+(\S+)', line, re.IGNORECASE)
                if match:
                    username = match.group(1)
                    # password_plaintext = match.group(2) - On ne stocke pas le password en clair
                    current_user = username
                    current_section = 'username'
                    # On ne peut pas récupérer le password depuis la config, on met un placeholder
                    users[username] = LocalUser(
                        username=username,
                        group='operators',  # groupe par défaut
                        password_plaintext=''  # vide, l'utilisateur devra le re-saisir
                    )
                continue
            
            # Groupe de l'utilisateur
            if current_section == 'username' and current_user and line.startswith('group '):
                match = re.match(r'group\s+(\S+)', line, re.IGNORECASE)
                if match:
                    group_name = match.group(1)
                    if current_user in users:
                        users[current_user].group = group_name
                continue
            
            # Fermeture de section username
            if line == 'exit' and current_section == 'username':
                current_section = None
                current_user = None
                continue
        
        # Retourner l'état parsé
        return SwitchState(
            vlans=vlans,
            ports=ports,
            users=users,
            user_groups=user_groups
        )
