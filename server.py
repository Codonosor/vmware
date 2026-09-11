import json
import logging
from mcp.server.fastmcp import FastMCP
from utils.logger import setup_logging
from utils.config import Config
from core.vsphere_client import VSphereClient
from core.horizon_client import HorizonClient
from core.veeam_client import VeeamClient
from core.oneview_client import HPEOneViewClient

setup_logging()
logger = logging.getLogger("server")

mcp = FastMCP("DatacenterInfrastructureMCP")

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
def list_horizon_desktop_pools() -> str:
    """Lista los pools de escritorios virtuales (Desktop Pools) en VMware Horizon."""
    client = HorizonClient(Config.HORIZON_SERVER, Config.HORIZON_DOMAIN, Config.HORIZON_USER, Config.HORIZON_PASSWORD)
    try:
        client.connect()
        pools = client.list_desktop_pools()
        return json.dumps(pools, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool list_horizon_desktop_pools: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def get_veeam_backup_status() -> str:
    """Revisa el estado de los últimos jobs de backup en Veeam Backup & Replication."""
    client = VeeamClient(Config.VEEAM_SERVER, Config.VEEAM_PORT, Config.VEEAM_USER, Config.VEEAM_PASSWORD)
    try:
        client.connect()
        status = client.get_last_backup_jobs_status()
        return json.dumps(status, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool get_veeam_backup_status: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

@mcp.tool()
def get_oneview_enclosures_status() -> str:
    """Obtiene el estado general de los enclosures de infraestructura en HPE OneView (Synergy 12000)."""
    client = HPEOneViewClient(Config.ONEVIEW_IP, Config.ONEVIEW_USER, Config.ONEVIEW_PASSWORD)
    try:
        client.connect()
        enclosures = client.get_enclosures_status()
        return json.dumps(enclosures, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error en tool get_oneview_enclosures_status: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.disconnect()

if __name__ == "__main__":
    logger.info("Iniciando servidor MCP de Datacenter...")
    mcp.run()
