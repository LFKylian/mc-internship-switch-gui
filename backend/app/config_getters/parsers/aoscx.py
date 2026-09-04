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
            "!Version AOS-CX",
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
        
        Format attendu :
        - vlan 1-2 (plage de VLANs)
        - vlan 3
        -   name VLAN 3
        -   description ...
        - interface 1/1/1
        -   no shutdown
        -   vlan trunk native 1
        -   vlan trunk allowed all
        - interface 1/1/2
        -   no shutdown
        -   vlan access 1
        - username admin group administrators password ciphertext ...
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
        in_interface_vlan_section = False
        
        for line in lines:
            line = line.strip()
            
            # Ignorer les commentaires et lignes vides
            if not line or line.startswith('!') or line.startswith('#'):
                continue
            
            # Détection des sections principales
            if line.startswith('hostname'):
                current_section = 'hostname'
                continue
            
            # Section VLAN (définition de VLANs)
            # Format: vlan 1-2 ou vlan 3
            if line.startswith('vlan ') and not line.startswith('vlan '):
                # Vérifier que ce n'est pas "interface vlan X"
                if 'interface vlan' not in line:
                    match = re.match(r'vlan\s+(\d+(?:-\d+)?)', line)
                    if match:
                        vlan_range = match.group(1)
                        if '-' in vlan_range:
                            # Plage de VLANs : vlan 1-2
                            start, end = map(int, vlan_range.split('-'))
                            for vlan_id in range(start, end + 1):
                                vlans[vlan_id] = Vlan(id=vlan_id, name="")
                        else:
                            # VLAN unique : vlan 3
                            current_vlan_id = int(vlan_range)
                            current_section = 'vlan_def'
                            vlans[current_vlan_id] = Vlan(id=current_vlan_id, name="")
                continue
            
            # Nom du VLAN (dans la section de définition de VLAN)
            if current_section == 'vlan_def' and line.startswith('name '):
                match = re.match(r'name\s+(.+)', line)
                if match:
                    vlan_name = match.group(1).strip().strip('"')
                    if current_vlan_id and current_vlan_id in vlans:
                        vlans[current_vlan_id].name = vlan_name
                continue
            
            # Description du VLAN
            if current_section == 'vlan_def' and line.startswith('description '):
                match = re.match(r'description\s+(.+)', line)
                if match:
                    description = match.group(1).strip().strip('"')
                    if current_vlan_id and current_vlan_id in vlans:
                        vlans[current_vlan_id].description = description if description != '.' else None
                continue
            
            # Fermeture de section vlan_def
            if current_section == 'vlan_def' and (line == 'exit' or not line.startswith(' ') and not line.startswith('\t')):
                current_section = None
                current_vlan_id = None
                continue
            
            # Section Interface (ports physiques)
            if line.startswith('interface ') and not line.startswith('interface vlan'):
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
            
            # Fermeture de section interface (port physique)
            if current_section == 'interface' and line == 'exit':
                current_section = None
                current_port_id = None
                continue
            
            # Configuration dans une interface (port physique)
            if current_section == 'interface' and current_port_id:
                port = ports[current_port_id]
                
                # Port activé (no shutdown = enabled)
                if line.lower() == 'no shutdown':
                    port.enabled = True
                elif line.lower() == 'shutdown':
                    port.enabled = False
                
                # Mode trunk avec VLAN natif
                # Format: vlan trunk native 1
                match = re.match(r'vlan\s+trunk\s+native\s+(\d+)', line, re.IGNORECASE)
                if match:
                    port.mode = PortMode.TRUNK
                    port.native_vlan = int(match.group(1))
                
                # Mode trunk avec VLANs autorisés
                # Format: vlan trunk allowed all
                if 'vlan trunk allowed all' in line.lower():
                    port.mode = PortMode.TRUNK
                    # "all" signifie tous les VLANs, mais on ne peut pas les lister tous
                    # On va laisser tagged_vlans vide et le frontend gérera
                
                # Mode trunk avec VLANs spécifiques
                # Format: vlan trunk allowed 1-10,20,30
                match = re.match(r'vlan\s+trunk\s+allowed\s+(.+)', line, re.IGNORECASE)
                if match:
                    port.mode = PortMode.TRUNK
                    vlan_list_str = match.group(1)
                    # Parser la liste de VLANs (ex: "1-10,20,30" -> [1,2,3,...,10,20,30])
                    port.tagged_vlans = self._parse_vlan_list(vlan_list_str)
                
                # Mode access avec VLAN
                # Format: vlan access 1
                match = re.match(r'vlan\s+access\s+(\d+)', line, re.IGNORECASE)
                if match:
                    port.mode = PortMode.ACCESS
                    port.native_vlan = int(match.group(1))
                
                # Description
                match = re.search(r'description\s+"([^"]*)"', line, re.IGNORECASE)
                if match:
                    port.description = match.group(1)
                continue
            
            # Section Interface VLAN (configuration IP des VLANs)
            if line.startswith('interface vlan '):
                match = re.match(r'interface\s+vlan\s+(\d+)', line)
                if match:
                    current_port_id = f"vlan_{match.group(1)}"
                    current_section = 'interface_vlan'
                    in_interface_vlan_section = True
                continue
            
            # Fermeture de section interface vlan
            if current_section == 'interface_vlan' and line == 'exit':
                current_section = None
                current_port_id = None
                in_interface_vlan_section = False
                continue
            
            # Section utilisateurs locaux
            # Format: username admin group administrators password ciphertext ...
            if line.startswith('username ') and 'password' in line.lower():
                # Extraire le username et le groupe
                # Format: username admin group administrators password ...
                match = re.match(r'username\s+(\S+)\s+group\s+(\S+)', line, re.IGNORECASE)
                if match:
                    username = match.group(1)
                    group_name = match.group(2)
                    # On ne peut pas récupérer le password depuis la config (ciphertext)
                    users[username] = LocalUser(
                        username=username,
                        group=group_name,
                        password_plaintext=''  # vide, l'utilisateur devra le re-saisir
                    )
                continue
        
        # Retourner l'état parsé
        return SwitchState(
            vlans=vlans,
            ports=ports,
            users=users,
            user_groups=user_groups
        )
    
    def _parse_vlan_list(self, vlan_list_str: str) -> List[int]:
        """
        Parse une liste de VLANs au format ArubaOS-CX.
        Exemples : "1-10" -> [1,2,3,4,5,6,7,8,9,10]
                  "1-5,10,15-20" -> [1,2,3,4,5,10,15,16,17,18,19,20]
                  "all" -> [] (tous les VLANs, on ne peut pas les lister)
        """
        vlan_list_str = vlan_list_str.strip()
        
        if vlan_list_str.lower() == 'all':
            return []  # Tous les VLANs, on retourne vide
        
        result = []
        # Remplacer les virgules par des espaces pour simplifier
        vlan_list_str = vlan_list_str.replace(',', ' ')
        
        for part in vlan_list_str.split():
            if '-' in part:
                # Plage de VLANs
                start, end = map(int, part.split('-'))
                result.extend(range(start, end + 1))
            else:
                # VLAN unique
                result.append(int(part))
        
        return result
