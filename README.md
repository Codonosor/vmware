# Datacenter Infrastructure MCP Server

Servidor basado en el **Model Context Protocol (MCP)** desarrollado en Python para la administración automatizada y gestión de infraestructura de centros de datos (VMware vSphere 7.0, VMware Horizon 8.11, Veeam Backups 12 y HPE OneView / Synergy 12000) mediante lenguaje natural.

---

## Estructura del Proyecto

```text
/mcp-datacenter
 ├── core/
 │    ├── __init__.py
 │    ├── vsphere_client.py
 │    ├── horizon_client.py
 │    ├── veeam_client.py
 │    ├── oneview_client.py
 │    └── workflows.py
 ├── utils/
 │    ├── __init__.py
 │    ├── logger.py
 │    └── config.py
 ├── server.py
 ├── requirements.txt
 └── .env
```

---

## Prerrequisitos e Instalación

1. Asegúrate de tener Python 3.10 o superior instalado.
2. Clona o sitúate en el directorio del proyecto e instala las dependencias:

```bash
pip install -r requirements.txt
```

---

## Configuración del Entorno (`.env`)

Crea y configura tu archivo `.env` en la raíz del proyecto basándote en la plantilla provista:

```env
# vSphere vCenter Configuration
VSPHERE_SERVER=vcenter.local
VSPHERE_USER=administrator@vsphere.local
VSPHERE_PASSWORD=tu_contraseña

# VMware Horizon Configuration
HORIZON_SERVER=horizon.local
HORIZON_DOMAIN=local
HORIZON_USER=admin
HORIZON_PASSWORD=tu_contraseña

# Veeam Backup Configuration
VEEAM_SERVER=veeam.local
VEEAM_PORT=9399
VEEAM_USER=administrator
VEEAM_PASSWORD=tu_contraseña

# HPE OneView Configuration
ONEVIEW_IP=oneview.local
ONEVIEW_USER=administrator
ONEVIEW_PASSWORD=tu_contraseña
```

---

## Ejecución del Servidor MCP

Para iniciar el servidor MCP utilizando el transporte por `stdio` (estándar para integración con clientes MCP como Claude Desktop):

```bash
python server.py
```

Los registros de actividad y errores se almacenarán automáticamente en el archivo `datacenter_mcp.log` para no interferir con la comunicación JSON-RPC del transporte `stdio`.

---

## Herramientas (Tools) Expuestas por MCP

El servidor expone un conjunto completo de herramientas organizadas por plataforma y flujos automatizados:

### 1. VMware vSphere (Golden Images & VMs)
- `list_vsphere_alarms`: Lista VMs con alarmas activas.
- `get_vm_power_state`: Obtiene el estado de energía de una VM.
- `power_on_vm`: Enciende una VM y opcionalmente espera a VMware Tools.
- `power_off_vm`: Apaga una VM (ordenado con fallback a forzado).
- `wait_for_guest_tools`: Espera activa de VMware Tools en el invitado.
- `create_snapshot`: Crea un snapshot (`memory=False` por defecto para Instant Clones).
- `list_snapshots`: Lista y aplana el árbol de snapshots.
- `get_latest_snapshot`: Obtiene el snapshot actual (`currentSnapshot`).
- `revert_to_snapshot`: Revierte una VM a un snapshot específico.
- `delete_snapshot`: Elimina un snapshot.
- `run_command_in_guest`: Ejecuta comandos dentro del invitado (Guest Operations).

### 2. VMware Horizon 8.11 (Instant Clones & Pools)
- `list_horizon_desktop_pools`: Lista los Desktop Pools.
- `get_pool_details`: Obtiene detalles de un pool.
- `create_instant_clone_pool`: Crea un nuevo Instant Clone Pool.
- `update_pool_settings`: Actualiza configuración de un pool.
- `enable_provisioning`: Habilita/deshabilita el aprovisionamiento.
- `enable_pool`: Habilita/deshabilita un pool.
- `schedule_push_image`: Programa Push Image (Recompose).
- `get_push_image_status`: Consulta el estado del Push Image.
- `cancel_push_image`: Cancela una operación de Push Image.
- `list_active_sessions`: Lista sesiones de usuario activas.
- `disconnect_session`: Desconecta una sesión de usuario.
- `logoff_session`: Cierra sesión (logoff) de un usuario.
- `send_message_to_session`: Envía un mensaje a una sesión.
- `send_broadcast_message_to_pool`: Envía un mensaje broadcast a un pool.
- `list_machines_in_pool`: Lista las VMs de un pool.
- `get_error_machines`: Obtiene máquinas en estado de error.
- `recreate_machine`: Recrea una máquina con error en Horizon.

### 3. Veeam Backup & Replication 12
- `get_veeam_backup_status`: Revisa el estado de los últimos jobs de backup.

### 4. HPE OneView (Synergy 12000)
- `get_oneview_enclosures_status`: Obtiene el estado general de los enclosures.

### 5. Workflows Automatizados (Golden Images & Despliegue)
- `workflow_prepare_golden_image_tool`: Enciende la Golden Image y espera a VMware Tools.
- `workflow_seal_and_snapshot_tool`: Apaga de forma ordenada la Golden Image y toma snapshot con `memory=False`.
- `workflow_deploy_image_to_pools_tool`: Dispara el despliegue (Push Image) de la imagen hacia múltiples Desktop Pools de Horizon.

---

## Integración con Clientes MCP (Ej. Claude Desktop)

Para registrar este servidor en tu cliente MCP (como Claude Desktop), añade la siguiente configuración en tu archivo de configuración de MCP (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "datacenter-mcp": {
      "command": "python",
      "args": [
        "C:\\Users\\EJTO12241897\\Documents\\vmware\\server.py"
      ]
    }
  }
}
```
