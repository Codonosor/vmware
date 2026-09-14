import logging
from utils.config import Config
from core.vsphere_client import VSphereClient
from core.horizon_client import HorizonClient

logger = logging.getLogger(__name__)

def workflow_prepare_golden_image(vm_name: str) -> dict:
    """Enciende la VM base (Golden Image) y espera a que VMware Tools esté operativa."""
    vsphere = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    try:
        vsphere.connect()
        logger.info(f"Workflow: Preparando Golden Image '{vm_name}' (Encendido y verificación de Tools)...")
        
        power_result = vsphere.power_on_vm(vm_name, wait_for_tools=True, timeout_sec=300)
        
        return {
            "status": "success",
            "vm_name": vm_name,
            "power_result": power_result,
            "message": f"Golden Image '{vm_name}' preparada y lista para modificaciones."
        }
    except Exception as e:
        logger.error(f"Error en workflow_prepare_golden_image para '{vm_name}': {e}")
        return {"status": "error", "vm_name": vm_name, "error": str(e)}
    finally:
        vsphere.disconnect()

def workflow_seal_and_snapshot(vm_name: str, snapshot_name: str, description: str, run_osot: bool = False) -> dict:
    """Apaga la VM de forma ordenada, valida estado poweredOff y toma snapshot con memory=False."""
    vsphere = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    try:
        vsphere.connect()
        logger.info(f"Workflow: Sellando y creando snapshot para Golden Image '{vm_name}'...")

        if run_osot:
            logger.info("Ejecutando OSOT (Optimization Tool) o tareas de limpieza previas (simulado/hook)...")
            # Aquí se podría integrar la ejecución de scripts en guest si fuera necesario.

        # Apagado ordenado
        off_result = vsphere.power_off_vm(vm_name, graceful=True, timeout_sec=180)
        
        # Validar estado poweredOff
        state = vsphere.get_vm_power_state(vm_name)
        if state != "poweredOff":
            raise Exception(f"No se pudo asegurar el apagado completo de la VM '{vm_name}'. Estado actual: {state}")

        # Tomar snapshot con memory=False (requisito estricto para Instant Clones)
        snap_result = vsphere.create_snapshot(
            vm_name=vm_name,
            snapshot_name=snapshot_name,
            description=description,
            memory=False,
            quiesce=True
        )

        return {
            "status": "success",
            "vm_name": vm_name,
            "snapshot_name": snapshot_name,
            "power_off_result": off_result,
            "snapshot_result": snap_result,
            "message": f"Golden Image '{vm_name}' sellada y snapshot '{snapshot_name}' creado exitosamente."
        }
    except Exception as e:
        logger.error(f"Error en workflow_seal_and_snapshot para '{vm_name}': {e}")
        return {"status": "error", "vm_name": vm_name, "error": str(e)}
    finally:
        vsphere.disconnect()

def workflow_deploy_image_to_pools(vm_name: str, snapshot_name: str, target_pools: list[str]) -> list[dict]:
    """Resuelve IDs de la VM y snapshot en vSphere, valida pools en Horizon y dispara push-image (recompose)."""
    vsphere = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    horizon = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    
    results = []
    try:
        vsphere.connect()
        horizon.connect()

        logger.info(f"Workflow: Desplegando imagen de VM '{vm_name}' (Snapshot: '{snapshot_name}') a pools: {target_pools}")

        # Obtener la VM y validar que exista
        vm_obj = vsphere._get_vm_by_name(vm_name)
        parent_vm_id = str(vm_obj._moId) # MoId de vSphere como identificador

        # Validar y buscar snapshot
        snapshots = vsphere.list_snapshots(vm_name)
        target_snap = next((s for s in snapshots if s["name"] == snapshot_name), None)
        if not target_snap:
            raise ValueError(f"No se encontró el snapshot '{snapshot_name}' en la VM '{vm_name}'.")
        
        # En Horizon, necesitamos el ID del snapshot (en API REST se suele usar el nombre o ID según versión).
        # Usaremos snapshot_name como referencia para el push image spec de Horizon.
        snapshot_id = snapshot_name 

        for pool_id in target_pools:
            try:
                logger.info(f"Procesando Push Image para el pool de Horizon '{pool_id}'...")
                
                # Opcional: Habilitar aprovisionamiento si estuviera deshabilitado
                horizon.enable_provisioning(pool_id, True)

                # Disparar Push Image
                push_res = horizon.schedule_push_image(
                    pool_id=pool_id,
                    parent_vm_id=parent_vm_id,
                    snapshot_id=snapshot_id,
                    logoff_policy="FORCE_LOGOFF"
                )

                results.append({
                    "pool_id": pool_id,
                    "status": "success",
                    "push_image_response": push_res
                })
            except Exception as pool_err:
                logger.error(f"Error al actualizar el pool '{pool_id}': {pool_err}")
                results.append({
                    "pool_id": pool_id,
                    "status": "error",
                    "error": str(pool_err)
                })

        return results
    except Exception as e:
        logger.error(f"Error general en workflow_deploy_image_to_pools: {e}")
        return [{"status": "error", "error": str(e)}]
    finally:
        vsphere.disconnect()
        horizon.disconnect()
