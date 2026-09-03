from app.domain.push import PushMethods
from app.config_pushers.ssh import SSHConfigPusher
from app.config_pushers.factory import PusherFactory

# Enregistrement des implémentations auprès de la fabrique
PusherFactory.register(PushMethods.SSH.value, SSHConfigPusher())