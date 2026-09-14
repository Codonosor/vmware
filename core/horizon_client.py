import logging
import requests
import urllib3

# Deshabilitar warnings de certificados SSL autofirmados
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class HorizonClient:
    def __init__(self, server, domain, user, password):
        self.server = server.rstrip('/')
        self.domain = domain
        self.user = user
        self.password = password
        self.token = None
        self.session = requests.Session()
        self.session.verify = False

    def connect(self):
        """Autentica contra la API REST de VMware Horizon y obtiene el token de sesión."""
        url = f"https://{self.server}/rest/v1/auth/login"
        payload = {
            "username": self.user,
            "password": self.password,
            "domain": self.domain
        }
        try:
            logger.info(f"Conectando a VMware Horizon API en {self.server}")
            response = self.session.post(url, json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token") or data.get("token")
                if self.token:
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    })
                logger.info("Autenticación exitosa en VMware Horizon.")
            elif response.status_code == 401:
                logger.error("Error de autenticación: Credenciales inválidas en VMware Horizon.")
                raise PermissionError("Credenciales inválidas para Horizon.")
            else:
                logger.error(f"Error HTTP {response.status_code} al conectar con Horizon: {response.text}")
                response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error("Timeout al intentar conectar con la API de VMware Horizon.")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Error de conexión con VMware Horizon ({self.server}): {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al conectar con Horizon: {e}")
            raise

    def disconnect(self):
        """Cierra la sesión en Horizon de manera limpia."""
        if self.token:
            url = f"https://{self.server}/rest/v1/auth/logout"
            try:
                self.session.post(url, timeout=10)
                logger.info("Sesión de Horizon cerrada limpiamente.")
            except Exception as e:
                logger.error(f"Error al cerrar sesión en Horizon: {e}")
            finally:
                self.token = None
                self.session.headers.pop("Authorization", None)

    def list_desktop_pools(self):
        """Lista los pools de escritorios virtuales (Desktop Pools) - Lectura."""
        url = f"https://{self.server}/rest/v1/inventory/desktop-pools"
        try:
            logger.info("Obteniendo lista de Desktop Pools desde Horizon...")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            pools = response.json()
            logger.info("Desktop Pools obtenidos exitosamente.")
            return pools
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al listar los Desktop Pools de Horizon: {e}")
            raise

    def get_pool_details(self, pool_id: str) -> dict:
        """Obtiene los detalles de un Desktop Pool específico."""
        url = f"https://{self.server}/rest/v1/inventory/desktop-pools/{pool_id}"
        try:
            logger.info(f"Obteniendo detalles del pool '{pool_id}'...")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener detalles del pool '{pool_id}': {e}")
            raise

    def create_instant_clone_pool(self, spec: dict) -> dict:
        """Crea un nuevo Desktop Pool de tipo Instant Clone."""
        url = f"https://{self.server}/rest/v1/inventory/desktop-pools"
        try:
            logger.info("Creando Desktop Pool de Instant Clone...")
            response = self.session.post(url, json=spec, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al crear Instant Clone Pool: {e}")
            raise

    def update_pool_settings(self, pool_id: str, data: dict) -> dict:
        """Actualiza la configuración de un Desktop Pool."""
        url = f"https://{self.server}/rest/v1/inventory/desktop-pools/{pool_id}"
        try:
            logger.info(f"Actualizando configuración del pool '{pool_id}'...")
            response = self.session.put(url, json=data, timeout=20)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al actualizar configuración del pool '{pool_id}': {e}")
            raise

    def enable_provisioning(self, pool_id: str, enabled: bool) -> dict:
        """Habilita o deshabilita el aprovisionamiento en un pool."""
        url = f"https://{self.server}/rest/v1/inventory/desktop-pools/{pool_id}/actions/enable-provisioning"
        payload = {"enabled": enabled}
        try:
            logger.info(f"Cambiando aprovisionamiento a {enabled} en pool '{pool_id}'...")
            response = self.session.post(url, json=payload, timeout=15)
            response.raise_for_status()
            return {"status": "success", "pool_id": pool_id, "provisioning_enabled": enabled}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al cambiar aprovisionamiento en pool '{pool_id}': {e}")
            raise

    def enable_pool(self, pool_id: str, enabled: bool) -> dict:
        """Habilita o deshabilita un Desktop Pool."""
        url = f"https://{self.server}/rest/v1/inventory/desktop-pools/{pool_id}/actions/enable"
        payload = {"enabled": enabled}
        try:
            logger.info(f"Cambiando estado habilitado a {enabled} en pool '{pool_id}'...")
            response = self.session.post(url, json=payload, timeout=15)
            response.raise_for_status()
            return {"status": "success", "pool_id": pool_id, "pool_enabled": enabled}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al cambiar estado habilitado en pool '{pool_id}': {e}")
            raise

    def schedule_push_image(self, pool_id: str, parent_vm_id: str, snapshot_id: str, logoff_policy: str = "FORCE_LOGOFF") -> dict:
        """Programa un Push Image (Recompose) para un Instant Clone Pool."""
        url = f"https://{self.server}/rest/v1/inventory/desktop-pools/{pool_id}/actions/push-image"
        payload = {
            "parent_vm_id": parent_vm_id,
            "snapshot_id": snapshot_id,
            "logoff_policy": logoff_policy
        }
        try:
            logger.info(f"Programando Push Image para el pool '{pool_id}' con VM '{parent_vm_id}'...")
            response = self.session.post(url, json=payload, timeout=20)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al programar Push Image en pool '{pool_id}': {e}")
            raise

    def get_push_image_status(self, pool_id: str) -> dict:
        """Obtiene el estado de la tarea de Push Image en un pool."""
        url = f"https://{self.server}/rest/v1/inventory/desktop-pools/{pool_id}/push-image-status"
        try:
            logger.info(f"Obteniendo estado de Push Image para el pool '{pool_id}'...")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener estado de Push Image en pool '{pool_id}': {e}")
            raise

    def cancel_push_image(self, pool_id: str) -> dict:
        """Cancela una operación de Push Image en curso."""
        url = f"https://{self.server}/rest/v1/inventory/desktop-pools/{pool_id}/actions/cancel-push-image"
        try:
            logger.info(f"Cancelando Push Image en pool '{pool_id}'...")
            response = self.session.post(url, timeout=15)
            response.raise_for_status()
            return {"status": "success", "pool_id": pool_id}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al cancelar Push Image en pool '{pool_id}': {e}")
            raise

    def list_active_sessions(self, pool_id: str = None) -> list:
        """Lista las sesiones activas de usuarios, opcionalmente filtradas por pool."""
        url = f"https://{self.server}/rest/v1/monitor/sessions"
        if pool_id:
            url += f"?desktop_pool_id={pool_id}"
        try:
            logger.info("Listando sesiones activas en Horizon...")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al listar sesiones activas: {e}")
            raise

    def disconnect_session(self, session_id: str) -> dict:
        """Desconecta una sesión de usuario activa."""
        url = f"https://{self.server}/rest/v1/monitor/sessions/{session_id}/actions/disconnect"
        try:
            logger.info(f"Desconectando sesión '{session_id}'...")
            response = self.session.post(url, timeout=15)
            response.raise_for_status()
            return {"status": "success", "session_id": session_id}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al desconectar sesión '{session_id}': {e}")
            raise

    def logoff_session(self, session_id: str, force: bool = True) -> dict:
        """Cierra sesión (logoff) de un usuario."""
        url = f"https://{self.server}/rest/v1/monitor/sessions/{session_id}/actions/logoff"
        payload = {"force": force}
        try:
            logger.info(f"Cerrando sesión '{session_id}' (force={force})...")
            response = self.session.post(url, json=payload, timeout=15)
            response.raise_for_status()
            return {"status": "success", "session_id": session_id}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al cerrar sesión '{session_id}': {e}")
            raise

    def send_message_to_session(self, session_id: str, msg: str) -> dict:
        """Envía un mensaje de texto a una sesión de usuario específica."""
        url = f"https://{self.server}/rest/v1/monitor/sessions/{session_id}/actions/send-message"
        payload = {"message": msg}
        try:
            logger.info(f"Enviando mensaje a sesión '{session_id}'...")
            response = self.session.post(url, json=payload, timeout=15)
            response.raise_for_status()
            return {"status": "success", "session_id": session_id}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al enviar mensaje a sesión '{session_id}': {e}")
            raise

    def send_broadcast_message_to_pool(self, pool_id: str, msg: str) -> dict:
        """Envía un mensaje broadcast a todos los usuarios conectados en un pool."""
        url = f"https://{self.server}/rest/v1/inventory/desktop-pools/{pool_id}/actions/send-message"
        payload = {"message": msg}
        try:
            logger.info(f"Enviando mensaje broadcast al pool '{pool_id}'...")
            response = self.session.post(url, json=payload, timeout=15)
            response.raise_for_status()
            return {"status": "success", "pool_id": pool_id}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al enviar broadcast al pool '{pool_id}': {e}")
            raise

    def list_machines_in_pool(self, pool_id: str) -> list:
        """Lista las máquinas virtuales pertenecientes a un Desktop Pool."""
        url = f"https://{self.server}/rest/v1/inventory/desktop-pools/{pool_id}/machines"
        try:
            logger.info(f"Listando máquinas del pool '{pool_id}'...")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al listar máquinas del pool '{pool_id}': {e}")
            raise

    def get_error_machines(self) -> list:
        """Obtiene todas las máquinas que se encuentran en estado de error en Horizon."""
        url = f"https://{self.server}/rest/v1/monitor/machines?status=ERROR"
        try:
            logger.info("Buscando máquinas con errores en Horizon...")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener máquinas con errores: {e}")
            raise

    def recreate_machine(self, machine_id: str) -> dict:
        """Recrea (recreate) una máquina virtual con error en Horizon."""
        url = f"https://{self.server}/rest/v1/inventory/machines/{machine_id}/actions/recreate"
        try:
            logger.info(f"Recreando máquina '{machine_id}'...")
            response = self.session.post(url, timeout=20)
            response.raise_for_status()
            return {"status": "success", "machine_id": machine_id}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al recrear máquina '{machine_id}': {e}")
            raise
