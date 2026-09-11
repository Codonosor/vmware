import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # vSphere
    VSPHERE_SERVER = os.getenv("VSPHERE_SERVER")
    VSPHERE_USER = os.getenv("VSPHERE_USER")
    VSPHERE_PASSWORD = os.getenv("VSPHERE_PASSWORD")

    # Horizon
    HORIZON_SERVER = os.getenv("HORIZON_SERVER")
    HORIZON_DOMAIN = os.getenv("HORIZON_DOMAIN", "local")
    HORIZON_USER = os.getenv("HORIZON_USER")
    HORIZON_PASSWORD = os.getenv("HORIZON_PASSWORD")

    # Veeam
    VEEAM_SERVER = os.getenv("VEEAM_SERVER")
    VEEAM_PORT = int(os.getenv("VEEAM_PORT", 9399))
    VEEAM_USER = os.getenv("VEEAM_USER")
    VEEAM_PASSWORD = os.getenv("VEEAM_PASSWORD")

    # OneView
    ONEVIEW_IP = os.getenv("ONEVIEW_IP")
    ONEVIEW_USER = os.getenv("ONEVIEW_USER")
    ONEVIEW_PASSWORD = os.getenv("ONEVIEW_PASSWORD")
