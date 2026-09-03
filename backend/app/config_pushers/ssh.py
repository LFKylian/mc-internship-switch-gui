from netmiko import ConnectHandler
from app.config_pushers.base import ConfigPusher
from app.domain.push import SSHDeviceInfo


class SSHConfigPusher(ConfigPusher):
    def push_config(self, pushing_device_info: SSHDeviceInfo, commands: list[str]) -> str:
        # Conversion du modèle Pydantic en dictionnaire nettoyé pour Netmiko
        netmiko_args = pushing_device_info.to_netmiko_dict()
        
        with ConnectHandler(**netmiko_args) as net_connect:
            output = net_connect.send_config_set(commands)
            net_connect.save_config()
            return output