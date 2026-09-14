import json
import logging
from mcp.server.fastmcp import FastMCP
from utils.logger import setup_logging
from utils.config import Config
from core.vsphere_client import VSphereClient
from core.horizon_client import HorizonClient
from core.veeam_client import VeeamClient
from core.oneview_client import HPEOneViewClient
from core.workflows import (
    workflow_prepare_golden_image,
    workflow_seal_and_snapshot,
    workflow_deploy_image_to_pools
)

setup_logging()
logger = logging.getLogger("server")

mcp = FastMCP("DatacenterInfrastructureMCP")

# --- vSphere Tools ---
@mcp.tool()
def list_vsphere_alarms() -> str:
    """Lista las máquinas virtuales de vSphere que tienen alarmas activas."""
    client = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    try:
        client.connect()
        vms = client.list_vms_with_active_alarms()
        return json.dumps(vms, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool list_vsphere_alarms: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def get_vm_power_state(vm_name: str) -> str:
    """Retorna el estado de energía actual de una máquina virtual en vSphere."""
    client = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    try:
        client.connect()
        state = client.get_vm_power_state(vm_name)
        return json.dumps({"vm_name": vm_name, "power_state": state}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en get_vm_power_state: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def power_on_vm(vm_name: str, wait_for_tools: bool = True, timeout_sec: int = 300) -> str:
    """Enciende una máquina virtual en vSphere y opcionalmente espera a las VMware Tools."""
    client = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    try:
        client.connect()
        res = client.power_on_vm(vm_name, wait_for_tools=wait_for_tools, timeout_sec=timeout_sec)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en power_on_vm: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def power_off_vm(vm_name: str, graceful: bool = True, timeout_sec: int = 180) -> str:
    """Apaga una máquina virtual en vSphere (con apagado ordenado y fallback a forzado)."""
    client = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    try:
        client.connect()
        res = client.power_off_vm(vm_name, graceful=graceful, timeout_sec=timeout_sec)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en power_off_vm: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def wait_for_guest_tools(vm_name: str, timeout_sec: int = 300) -> str:
    """Espera activa hasta que las VMware Tools estén operativas en el invitado."""
    client = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    try:
        client.connect()
        ok = client.wait_for_guest_tools(vm_name, timeout_sec=timeout_sec)
        return json.dumps({"vm_name": vm_name, "tools_ready": ok}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en wait_for_guest_tools: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def create_snapshot(vm_name: str, snapshot_name: str, description: str, memory: bool = False, quiesce: bool = True) -> str:
    """Crea un snapshot de una máquina virtual en vSphere (memory=False por defecto para Instant Clones)."""
    client = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    try:
        client.connect()
        res = client.create_snapshot(vm_name, snapshot_name, description, memory=memory, quiesce=quiesce)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en create_snapshot: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def list_snapshots(vm_name: str) -> str:
    """Lista y aplana el árbol de snapshots de una máquina virtual en vSphere."""
    client = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    try:
        client.connect()
        snaps = client.list_snapshots(vm_name)
        return json.dumps(snaps, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en list_snapshots: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def get_latest_snapshot(vm_name: str) -> str:
    """Obtiene información del snapshot actual (currentSnapshot) de una VM."""
    client = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    try:
        client.connect()
        snap = client.get_latest_snapshot(vm_name)
        return json.dumps(snap, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en get_latest_snapshot: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def revert_to_snapshot(vm_name: str, snapshot_name: str) -> str:
    """Revierte una máquina virtual en vSphere a un snapshot específico."""
    client = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    try:
        client.connect()
        res = client.revert_to_snapshot(vm_name, snapshot_name)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en revert_to_snapshot: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def delete_snapshot(vm_name: str, snapshot_name: str) -> str:
    """Elimina un snapshot específico de una máquina virtual en vSphere."""
    client = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    try:
        client.connect()
        res = client.delete_snapshot(vm_name, snapshot_name)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en delete_snapshot: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def run_command_in_guest(vm_name: str, user: str, password: str, program_path: str, args: str) -> str:
    """Ejecuta un comando dentro del sistema operativo invitado usando vSphere Guest Operations."""
    client = VSphereClient(Config.VSPHERE_SERVER, Config.VSPHERE_USER, Config.VSPHERE_PASSWORD)
    try:
        client.connect()
        pid = client.run_command_in_guest(vm_name, user, password, program_path, args)
        return json.dumps({"vm_name": vm_name, "pid": pid, "status": "success"}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en run_command_in_guest: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()


# --- Horizon Tools ---
@mcp.tool()
def list_horizon_desktop_pools() -> str:
    """Lista los pools de escritorios virtuales (Desktop Pools) en VMware Horizon."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        pools = client.list_desktop_pools()
        return json.dumps(pools, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en list_horizon_desktop_pools: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def get_pool_details(pool_id: str) -> str:
    """Obtiene los detalles de un Desktop Pool específico en VMware Horizon."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        details = client.get_pool_details(pool_id)
        return json.dumps(details, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en get_pool_details: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def create_instant_clone_pool(spec_json: str) -> str:
    """Crea un nuevo Instant Clone Desktop Pool en Horizon a partir de una especificación JSON."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        spec = json.loads(spec_json)
        res = client.create_instant_clone_pool(spec)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en create_instant_clone_pool: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def update_pool_settings(pool_id: str, data_json: str) -> str:
    """Actualiza la configuración de un Desktop Pool en Horizon."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        data = json.loads(data_json)
        res = client.update_pool_settings(pool_id, data)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en update_pool_settings: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def enable_provisioning(pool_id: str, enabled: bool) -> str:
    """Habilita o deshabilita el aprovisionamiento en un Desktop Pool de Horizon."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        res = client.enable_provisioning(pool_id, enabled)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en enable_provisioning: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def enable_pool(pool_id: str, enabled: bool) -> str:
    """Habilita o deshabilita un Desktop Pool en Horizon."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        res = client.enable_pool(pool_id, enabled)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en enable_pool: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def schedule_push_image(pool_id: str, parent_vm_id: str, snapshot_id: str, logoff_policy: str = "FORCE_LOGOFF") -> str:
    """Programa una actualización de imagen (Push Image / Recompose) para un Instant Clone Pool."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        res = client.schedule_push_image(pool_id, parent_vm_id, snapshot_id, logoff_policy)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en schedule_push_image: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def get_push_image_status(pool_id: str) -> str:
    """Obtiene el estado de la operación Push Image en un Desktop Pool."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        status = client.get_push_image_status(pool_id)
        return json.dumps(status, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en get_push_image_status: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def cancel_push_image(pool_id: str) -> str:
    """Cancela una operación de Push Image en curso para un pool."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        res = client.cancel_push_image(pool_id)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en cancel_push_image: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def list_active_sessions(pool_id: str = None) -> str:
    """Lista las sesiones de usuario activas en Horizon, opcionalmente filtradas por pool_id."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        sessions = client.list_active_sessions(pool_id=pool_id)
        return json.dumps(sessions, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en list_active_sessions: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def disconnect_session(session_id: str) -> str:
    """Desconecta una sesión de usuario activa en Horizon."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        res = client.disconnect_session(session_id)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en disconnect_session: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def logoff_session(session_id: str, force: bool = True) -> str:
    """Cierra la sesión (logoff) de un usuario en Horizon."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        res = client.logoff_session(session_id, force=force)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en logoff_session: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def send_message_to_session(session_id: str, message: str) -> str:
    """Envía un mensaje de texto a una sesión de usuario específica en Horizon."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        res = client.send_message_to_session(session_id, message)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en send_message_to_session: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def send_broadcast_message_to_pool(pool_id: str, message: str) -> str:
    """Envía un mensaje broadcast a todas las sesiones activas de un pool en Horizon."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        res = client.send_broadcast_message_to_pool(pool_id, message)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en send_broadcast_message_to_pool: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def list_machines_in_pool(pool_id: str) -> str:
    """Lista las máquinas virtuales pertenecientes a un Desktop Pool en Horizon."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        machines = client.list_machines_in_pool(pool_id)
        return json.dumps(machines, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en list_machines_in_pool: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def get_error_machines() -> str:
    """Obtiene todas las máquinas virtuales que se encuentran en estado de error en Horizon."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        machines = client.get_error_machines()
        return json.dumps(machines, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en get_error_machines: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def recreate_machine(machine_id: str) -> str:
    """Recrea una máquina virtual con error en Horizon."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        res = client.recreate_machine(machine_id)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en recreate_machine: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()


# --- Other Infrastructure Tools ---
@mcp.tool()
def get_veeam_backup_status() -> str:
    """Revisa el estado de los últimos jobs de backup en Veeam Backup & Replication."""
    client = VeeamClient(Config.VEEAM_SERVER, Config.VEEAM_PORT, Config.VEEAM_USER, Config.VEEAM_PASSWORD)
    try:
        client.connect()
        status = client.get_last_backup_jobs_status()
        return json.dumps(status, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en get_veeam_backup_status: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def get_oneview_enclosures_status() -> str:
    """Obtiene el estado general de los enclosures de infraestructura en HPE OneView (Synergy 12000)."""
    client = HPEOneViewClient(Config.ONEVIEW_IP, Config.ONEVIEW_USER, Config.ONEVIEW_PASSWORD)
    try:
        client.connect()
        enclosures = client.get_oneview_enclosures_status() if hasattr(client, 'get_oneview_enclosures_status') else client.get_enclosures_status()
        return json.dumps(enclosures, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en get_oneview_enclosures_status: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()


# --- Workflows Tools ---
@mcp.tool()
def workflow_prepare_golden_image_tool(vm_name: str) -> str:
    """Workflow: Enciende la Golden Image base en vSphere y espera a que VMware Tools esté operativa."""
    res = workflow_prepare_golden_image(vm_name)
    return json.dumps(res, indent=2, ensure_ascii=False)

@mcp.tool()
def workflow_seal_and_snapshot_tool(vm_name: str, snapshot_name: str, description: str, run_osot: bool = False) -> str:
    """Workflow: Apaga ordenadamente la Golden Image en vSphere y crea snapshot con memory=False para Instant Clones."""
    res = workflow_seal_and_snapshot(vm_name, snapshot_name, description, run_osot=run_osot)
    return json.dumps(res, indent=2, ensure_ascii=False)

@mcp.tool()
def workflow_deploy_image_to_pools_tool(vm_name: str, snapshot_name: str, target_pools_json: str) -> str:
    """Workflow: Despliega una imagen (Push Image / Recompose) desde una Golden Image y snapshot hacia una lista JSON de pools de Horizon."""
    try:
        target_pools = json.loads(target_pools_json)
        res = workflow_deploy_image_to_pools(vm_name, snapshot_name, target_pools)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en workflow_deploy_image_to_pools_tool: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    logger.info("Iniciando servidor MCP de Datacenter con soporte avanzado para Horizon & vSphere...")
    mcp.run()
