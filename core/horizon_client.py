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
