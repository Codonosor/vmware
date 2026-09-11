import logging

def setup_logging():
    logging.basicConfig(
        filename="datacenter_mcp.log",
        filemode="a",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
