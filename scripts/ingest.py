import os
import shutil
import logging
from pathlib import Path
import kagglehub
from utils import load_config, setup_logging, get_project_root

def run_ingestion():
    """
    Downloads the YouTube trending dataset from Kaggle using kagglehub
    and copies the specified CSV and JSON category files to data/raw.
    """
    # Setup logger and configurations
    logger = setup_logging("ingest")
    logger.info("Starting ingestion phase...")
    
    try:
        config = load_config()
        project_root = get_project_root()
        
        # Define and create target raw data directory
        raw_dir = project_root / config.get("raw_data_dir", "data/raw")
        raw_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Target raw directory ready: {raw_dir}")
        
        # Download the dataset via kagglehub
        dataset_handle = config.get("kaggle_dataset", "datasnaek/youtube-new")
        logger.info(f"Downloading dataset '{dataset_handle}' via kagglehub...")
        
        # This download is cached locally by kagglehub
        downloaded_path_str = kagglehub.dataset_download(dataset_handle)
        downloaded_path = Path(downloaded_path_str)
        logger.info(f"Dataset successfully downloaded/located at cache: {downloaded_path}")
        
        # Retrieve selected regions from configuration
        regions = config.get("regions", ["US", "CA", "GB", "IN", "DE", "FR"])
        logger.info(f"Configured regions to ingest: {regions}")
        
        # Check files in downloaded directory and copy selected ones
        downloaded_files = list(downloaded_path.glob("*"))
        logger.info(f"Found {len(downloaded_files)} total files in download cache.")
        
        copied_files_count = 0
        for region in regions:
            # 1. Copy CSV file for region (e.g. USvideos.csv)
            csv_name = f"{region}videos.csv"
            src_csv = downloaded_path / csv_name
            dest_csv = raw_dir / csv_name
            
            if src_csv.exists():
                logger.info(f"Copying {csv_name} to raw folder...")
                shutil.copy2(src_csv, dest_csv)
                copied_files_count += 1
            else:
                logger.warning(f"Expected CSV file not found in cache: {src_csv}")
                
            # 2. Copy Category JSON file for region (e.g. US_category_id.json)
            json_name = f"{region}_category_id.json"
            src_json = downloaded_path / json_name
            dest_json = raw_dir / json_name
            
            if src_json.exists():
                logger.info(f"Copying {json_name} to raw folder...")
                shutil.copy2(src_json, dest_json)
                copied_files_count += 1
            else:
                logger.warning(f"Expected JSON file not found in cache: {src_json}")
                
        logger.info(f"Ingestion phase completed successfully. Copied {copied_files_count} files to {raw_dir}")
        return True
        
    except Exception as e:
        logger.exception(f"Ingestion failed with error: {e}")
        return False

if __name__ == "__main__":
    run_ingestion()
