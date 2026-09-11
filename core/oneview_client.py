import logging
from hpOneView.oneview_client import OneViewClient
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class HPEOneViewClient:
    def __init__(self, ip, user, password, api_version=1200):
        self.ip = ip
        self.user = user
        self.password = password
        self.api_version = api_version
        self.client = None
        self.config = {
            "ip": self.ip,
            "credentials": {
                "userName": self.user,
                "password": self.password
            },
            "api_version": self.api_version
        }

    def connect(self):
        """Conecta al appliance de HPE OneView y deshabilita la validación SSL."""
        try:
            logger.info(f"Conectando a HPE OneView en {self.ip}")
            self.client = OneViewClient(self.config)
            self.client.connection.cert_validation = False
            logger.info("Cliente de HPE OneView inicializado correctamente.")
        except Exception as e:
            logger.error(f"Error al conectar con HPE OneView ({self.ip}): {e}")
            raise

    def disconnect(self):
        """Limpia la referencia del cliente HPE OneView."""
        try:
            if self.client:
                self.client = None
                logger.info("Cliente HPE OneView desconectado limpiamente.")
        except Exception as e:
            logger.error(f"Error al desconectar de HPE OneView: {e}")

    def get_enclosures_status(self):
        """Obtiene el estado general de los enclosures (Synergy 12000) - Lectura."""
        if not self.client:
            raise ConnectionError("No hay una conexión activa con HPE OneView.")
        try:
            logger.info("Obteniendo estado de los enclosures desde HPE OneView...")
            enclosures = self.client.enclosures.get_all()
            
            summary = []
            for enc in enclosures:
                summary.append({
                    "name": enc.get("name"),
                    "status": enc.get("status"),
                    "state": enc.get("state"),
                    "serial_number": enc.get("serialNumber")
                })
                
            logger.info(f"Se obtuvieron {len(summary)} enclosures exitosamente.")
            return summary
        except Exception as e:
            logger.error(f"Error al obtener enclosures de HPE OneView: {e}")
            raise
