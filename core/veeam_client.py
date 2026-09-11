import logging
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class VeeamClient:
    def __init__(self, server, port, user, password):
        self.server = server.rstrip('/')
        self.port = port
        self.user = user
        self.password = password
        self.token = None
        self.base_url = f"https://{self.server}:{self.port}"
        self.session = requests.Session()
        self.session.verify = False

    def connect(self):
        """Autentica contra la API REST de Veeam Backup & Replication v12 y obtiene el token."""
        url = f"{self.base_url}/api/v1/auth/token"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        payload = {
            "grant_type": "password",
            "username": self.user,
            "password": self.password
        }
        try:
            logger.info(f"Conectando a Veeam Backup & Replication API en {self.server}:{self.port}")
            response = self.session.post(url, headers=headers, data=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if self.token:
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/json"
                    })
                logger.info("Autenticación exitosa en Veeam Backup & Replication.")
            elif response.status_code == 401:
                logger.error("Error de autenticación: Credenciales inválidas en Veeam.")
                raise PermissionError("Credenciales inválidas para Veeam.")
            else:
                logger.error(f"Error HTTP {response.status_code} al conectar con Veeam: {response.text}")
                response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error("Timeout al intentar conectar con la API de Veeam.")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Error de conexión con Veeam ({self.server}:{self.port}): {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al conectar con Veeam: {e}")
            raise

    def disconnect(self):
        """Cierra la sesión / revoca el token en Veeam."""
        url = f"{self.base_url}/api/v1/auth/logout"
        try:
            if self.token:
                self.session.post(url, timeout=10)
                logger.info("Sesión de Veeam cerrada limpiamente.")
        except Exception as e:
            logger.error(f"Error al cerrar sesión en Veeam: {e}")
        finally:
            self.token = None
            self.session.headers.pop("Authorization", None)

    def get_last_backup_jobs_status(self):
        """Revisa el estado de los últimos jobs de backup (Lectura)."""
        url = f"{self.base_url}/api/v1/jobs"
        try:
            logger.info("Obteniendo estado de los jobs de backup desde Veeam...")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            jobs_data = response.json()
            
            jobs_summary = []
            items = jobs_data.get("data", jobs_data) if isinstance(jobs_data, dict) else jobs_data
            
            for job in items:
                jobs_summary.append({
                    "job_name": job.get("name"),
                    "job_type": job.get("jobType"),
                    "last_run": job.get("lastRun"),
                    "last_result": job.get("lastResult")
                })
                
            logger.info("Estado de los jobs de backup obtenido exitosamente.")
            return jobs_summary
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al consultar los jobs de backup en Veeam: {e}")
            raise
