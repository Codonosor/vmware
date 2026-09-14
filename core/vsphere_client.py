import ssl
import logging
import time
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

    def _get_vm_by_name(self, vm_name: str) -> vim.VirtualMachine:
        """Busca y retorna un objeto vim.VirtualMachine por su nombre."""
        if not self.service_instance:
            raise ConnectionError("No hay una conexión activa con vCenter.")
        
        content = self.service_instance.RetrieveContent()
        container = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True
        )
        vms = container.view
        container.Destroy()

        for vm in vms:
            if vm.name == vm_name:
                return vm
        raise ValueError(f"No se encontró la máquina virtual '{vm_name}' en vCenter.")

    def _wait_for_task(self, task):
        """Espera a que una tarea de vSphere finalice."""
        while True:
            if task.info.state == 'success':
                return task.info.result
            if task.info.state == 'error':
                logger.error(f"Error en tarea vSphere: {task.info.error.msg}")
                raise Exception(task.info.error.msg)
            time.sleep(2)

    def get_vm_power_state(self, vm_name: str) -> str:
        """Retorna el estado de energía de una VM ('poweredOn', 'poweredOff', 'suspended')."""
        try:
            vm = self._get_vm_by_name(vm_name)
            state = str(vm.runtime.powerState)
            logger.info(f"Estado de energía de '{vm_name}': {state}")
            return state
        except Exception as e:
            logger.error(f"Error al obtener estado de energía de '{vm_name}': {e}")
            raise

    def wait_for_guest_tools(self, vm_name: str, timeout_sec: int = 300) -> bool:
        """Espera a que VMware Tools esté operativo en la VM."""
        vm = self._get_vm_by_name(vm_name)
        start_time = time.time()
        logger.info(f"Esperando a VMware Tools en '{vm_name}' (Timeout: {timeout_sec}s)...")
        
        while time.time() - start_time < timeout_sec:
            try:
                tools_status = vm.guest.toolsStatus
                if tools_status == vim.vm.GuestInfo.ToolsStatus.toolsRunning:
                    logger.info(f"VMware Tools están activas en '{vm_name}'.")
                    return True
            except Exception:
                pass
            time.sleep(5)
        
        logger.warning(f"Timeout esperando VMware Tools en '{vm_name}'.")
        return False

    def power_on_vm(self, vm_name: str, wait_for_tools: bool = True, timeout_sec: int = 300) -> dict:
        """Enciende una VM y opcionalmente espera a sus herramientas."""
        try:
            vm = self._get_vm_by_name(vm_name)
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                logger.info(f"La VM '{vm_name}' ya se encuentra encendida.")
                return {"status": "already_powered_on", "vm_name": vm_name}

            logger.info(f"Encendiendo VM '{vm_name}'...")
            task = vm.PowerOnVM_Task()
            self._wait_for_task(task)

            if wait_for_tools:
                self.wait_for_guest_tools(vm_name, timeout_sec)

            logger.info(f"VM '{vm_name}' encendida exitosamente.")
            return {"status": "success", "vm_name": vm_name, "power_state": "poweredOn"}
        except Exception as e:
            logger.error(f"Error al encender VM '{vm_name}': {e}")
            raise

    def power_off_vm(self, vm_name: str, graceful: bool = True, timeout_sec: int = 180) -> dict:
        """Apaga una VM de forma ordenada con fallback a apagado forzado."""
        try:
            vm = self._get_vm_by_name(vm_name)
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOff:
                logger.info(f"La VM '{vm_name}' ya se encuentra apagada.")
                return {"status": "already_powered_off", "vm_name": vm_name}

            if graceful:
                try:
                    logger.info(f"Intentando apagado ordenado (Guest Shutdown) en '{vm_name}'...")
                    vm.ShutdownGuest()
                    
                    start_time = time.time()
                    while time.time() - start_time < timeout_sec:
                        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOff:
                            logger.info(f"VM '{vm_name}' apagada ordenadamente.")
                            return {"status": "success", "vm_name": vm_name, "method": "graceful"}
                        time.sleep(5)
                    logger.warning(f"Timeout en apagado ordenado para '{vm_name}', aplicando apagado forzado...")
                except Exception as ex:
                    logger.warning(f"ShutdownGuest falló ({ex}), aplicando apagado forzado...")

            logger.info(f"Ejecutando apagado forzado (PowerOff) en '{vm_name}'...")
            task = vm.PowerOffVM_Task()
            self._wait_for_task(task)
            logger.info(f"VM '{vm_name}' apagada forzosamente.")
            return {"status": "success", "vm_name": vm_name, "method": "forced"}
        except Exception as e:
            logger.error(f"Error al apagar VM '{vm_name}': {e}")
            raise

    def create_snapshot(self, vm_name: str, snapshot_name: str, description: str, memory: bool = False, quiesce: bool = True) -> dict:
        """Crea un snapshot de la VM (por defecto memory=False para Instant Clones)."""
        try:
            vm = self._get_vm_by_name(vm_name)
            logger.info(f"Creando snapshot '{snapshot_name}' en VM '{vm_name}' (memory={memory}, quiesce={quiesce})...")
            task = vm.CreateSnapshot_Task(
                name=snapshot_name,
                description=description,
                memory=memory,
                quiesce=quiesce
            )
            self._wait_for_task(task)
            logger.info(f"Snapshot '{snapshot_name}' creado exitosamente en '{vm_name}'.")
            return {"status": "success", "vm_name": vm_name, "snapshot_name": snapshot_name}
        except Exception as e:
            logger.error(f"Error al crear snapshot en '{vm_name}': {e}")
            raise

    def list_snapshots(self, vm_name: str) -> list[dict]:
        """Lista y aplana el árbol de snapshots de una VM."""
        try:
            vm = self._get_vm_by_name(vm_name)
            snapshot_tree = vm.snapshot
            if not snapshot_tree or not snapshot_tree.rootSnapshotList:
                return []

            def _flatten_snapshots(tree_list):
                result = []
                for node in tree_list:
                    result.append({
                        "name": node.name,
                        "description": node.description,
                        "create_time": str(node.createTime),
                        "state": str(node.state)
                    })
                    if node.childSnapshotList:
                        result.extend(_flatten_snapshots(node.childSnapshotList))
                return result

            snapshots = _flatten_snapshots(snapshot_tree.rootSnapshotList)
            logger.info(f"Se listaron {len(snapshots)} snapshots para '{vm_name}'.")
            return snapshots
        except Exception as e:
            logger.error(f"Error al listar snapshots de '{vm_name}': {e}")
            raise

    def get_latest_snapshot(self, vm_name: str) -> dict:
        """Obtiene información del snapshot actual (currentSnapshot)."""
        try:
            vm = self._get_vm_by_name(vm_name)
            if not vm.snapshot or not vm.snapshot.currentSnapshot:
                return {"status": "no_snapshots", "vm_name": vm_name}

            curr = vm.snapshot.currentSnapshot
            return {
                "name": curr.name,
                "description": curr.description,
                "create_time": str(curr.createTime)
            }
        except Exception as e:
            logger.error(f"Error al obtener el último snapshot de '{vm_name}': {e}")
            raise

    def _find_snapshot_obj(self, snapshot_list, snapshot_name):
        for node in snapshot_list:
            if node.name == snapshot_name:
                return node.snapshot
            if node.childSnapshotList:
                found = self._find_snapshot_obj(node.childSnapshotList, snapshot_name)
                if found:
                    return found
        return None

    def revert_to_snapshot(self, vm_name: str, snapshot_name: str) -> dict:
        """Revierte la VM a un snapshot específico por su nombre."""
        try:
            vm = self._get_vm_by_name(vm_name)
            if not vm.snapshot or not vm.snapshot.rootSnapshotList:
                raise ValueError(f"La VM '{vm_name}' no tiene snapshots.")

            snap_obj = self._find_snapshot_obj(vm.snapshot.rootSnapshotList, snapshot_name)
            if not snap_obj:
                raise ValueError(f"No se encontró el snapshot '{snapshot_name}' en '{vm_name}'.")

            logger.info(f"Revirtiendo VM '{vm_name}' al snapshot '{snapshot_name}'...")
            task = snap_obj.RevertToSnapshot_Task()
            self._wait_for_task(task)
            logger.info(f"VM '{vm_name}' revertida exitosamente a '{snapshot_name}'.")
            return {"status": "success", "vm_name": vm_name, "snapshot_name": snapshot_name}
        except Exception as e:
            logger.error(f"Error al revertir snapshot en '{vm_name}': {e}")
            raise

    def delete_snapshot(self, vm_name: str, snapshot_name: str) -> dict:
        """Elimina un snapshot específico de una VM."""
        try:
            vm = self._get_vm_by_name(vm_name)
            if not vm.snapshot or not vm.snapshot.rootSnapshotList:
                raise ValueError(f"La VM '{vm_name}' no tiene snapshots.")

            snap_obj = self._find_snapshot_obj(vm.snapshot.rootSnapshotList, snapshot_name)
            if not snap_obj:
                raise ValueError(f"No se encontró el snapshot '{snapshot_name}' en '{vm_name}'.")

            logger.info(f"Eliminando snapshot '{snapshot_name}' en VM '{vm_name}'...")
            task = snap_obj.RemoveSnapshot_Task(removeChildren=False)
            self._wait_for_task(task)
            logger.info(f"Snapshot '{snapshot_name}' eliminado exitosamente.")
            return {"status": "success", "vm_name": vm_name, "snapshot_name": snapshot_name}
        except Exception as e:
            logger.error(f"Error al eliminar snapshot en '{vm_name}': {e}")
            raise

    def run_command_in_guest(self, vm_name: str, user: str, password: str, program_path: str, args: str) -> int:
        """Ejecuta un comando dentro del sistema operativo invitado usando Guest Operations."""
        try:
            vm = self._get_vm_by_name(vm_name)
            content = self.service_instance.RetrieveContent()
            
            creds = vim.vm.guest.NamePasswordAuthentication(username=user, password=password)
            pm = content.guestOperationsManager.processManager
            
            spec = vim.vm.guest.ProcessManager.ProgramSpec(
                programPath=program_path,
                arguments=args
            )
            
            logger.info(f"Ejecutando programa '{program_path}' en invitado '{vm_name}'...")
            pid = pm.StartProgramInGuest(vm, creds, spec)
            logger.info(f"Programa iniciado en '{vm_name}' con PID: {pid}")
            return pid
        except Exception as e:
            logger.error(f"Error al ejecutar comando en invitado '{vm_name}': {e}")
            raise
