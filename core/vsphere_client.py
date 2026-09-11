import ssl
import logging
from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim

logger = logging.getLogger(__name__)

class VSphereClient:
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        self.service_instance = None

    def connect(self):
        """Conecta al servidor vCenter ignorando certificados SSL."""
        try:
            logger.info(f"Conectando a vCenter: {self.host} con usuario {self.user}")
            self.service_instance = SmartConnectNoSSL(
                host=self.host,
                user=self.user,
                pwd=self.password
            )
            logger.info("Conexión exitosa a vCenter.")
        except vim.fault.InvalidLogin as e:
            logger.error(f"Error de autenticación en vCenter {self.host}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al conectar con vCenter {self.host}: {e}")
            raise

    def disconnect(self):
        """Cierra la conexión con vCenter de forma limpia."""
        if self.service_instance:
            try:
                Disconnect(self.service_instance)
                self.service_instance = None
                logger.info("Desconexión limpia de vCenter.")
            except Exception as e:
                logger.error(f"Error al desconectar de vCenter: {e}")

    def list_vms_with_active_alarms(self):
        """Lista las máquinas virtuales que tienen alarmas activas."""
        if not self.service_instance:
            raise ConnectionError("No hay una conexión activa con vCenter.")

        vms_with_alarms = []
        try:
            content = self.service_instance.RetrieveContent()
            container = content.viewManager.CreateContainerView(
                content.rootFolder, [vim.VirtualMachine], True
            )
            vms = container.view
            container.Destroy()

            for vm in vms:
                if vm.triggeredAlarmState:
                    alarms = [
                        {
                            "alarm_name": alarm_state.alarm.info.name,
                            "status": str(alarm_state.overallStatus)
                        }
                        for alarm_state in vm.triggeredAlarmState
                    ]
                    vms_with_alarms.append({
                        "vm_name": vm.name,
                        "power_state": str(vm.runtime.powerState),
                        "alarms": alarms
                    })
            logger.info(f"Se encontraron {len(vms_with_alarms)} VMs con alarmas activas.")
            return vms_with_alarms
        except Exception as e:
            logger.error(f"Error al listar VMs con alarmas activas: {e}")
            raise
