import os
import logging
import yaml
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
import time

def get_project_root() -> Path:
    """Returns the absolute path to the project root directory."""
    return Path(__file__).resolve().parent.parent

def load_config() -> dict:
    """Loads the YAML configuration file."""
    project_root = get_project_root()
    config_path = project_root / "config" / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
        
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

def setup_logging(name: str = "youtube_etl") -> logging.Logger:
    """Sets up unified logging for the ETL pipeline, outputting to both console and file."""
    config = load_config()
    project_root = get_project_root()
    
    # Create logs directory if it doesn't exist
    log_dir = project_root / config.get("log_dir", "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "pipeline.log"
    log_level_str = config.get("log_level", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Clear existing handlers to prevent duplicate logging
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # Formatter for log statements
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Prevent propagation to the root logger
    logger.propagate = False
    
    return logger

def get_db_engine(max_retries: int = 5, retry_delay: int = 5):
    """
    Creates and returns an SQLAlchemy connection engine for PostgreSQL.
    Implements retry logic in case the database is starting up.
    """
    config = load_config()
    db_config = config.get("database", {})
    
    host = db_config.get("host", "localhost")
    port = db_config.get("port", 5432)
    user = db_config.get("user", "postgres")
    password = db_config.get("password", "postgres")
    dbname = db_config.get("dbname", "youtube_trending")
    
    # Construct PostgreSQL connection URI
    # format: postgresql://username:password@host:port/database
    connection_uri = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    
    # Also support postgresql:// schema if needed for newer versions
    logger = logging.getLogger("youtube_etl")
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Connecting to database at {host}:{port}/{dbname} (Attempt {attempt}/{max_retries})...")
            engine = create_engine(connection_uri)
            # Test connection
            with engine.connect() as conn:
                logger.info("Database connection established successfully.")
            return engine
        except OperationalError as e:
            logger.warning(f"Database connection attempt {attempt} failed: {e}")
            if attempt == max_retries:
                logger.error("Max database connection retries reached. Connection failed.")
                raise e
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            
    raise RuntimeError("Could not connect to database.")
