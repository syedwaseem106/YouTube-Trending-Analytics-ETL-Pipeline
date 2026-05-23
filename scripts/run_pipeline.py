import time
import sys
import argparse
import logging
from utils import setup_logging
from ingest import run_ingestion
from transform import run_transformation
from load import run_loading

def main():
    """
    Main entry point for orchestrating the YouTube Trending Analytics ETL pipeline.
    Runs Ingest -> Transform -> Load sequentially and reports performance metrics.
    """
    parser = argparse.ArgumentParser(description="YouTube Trending ETL Pipeline")
    parser.add_argument('--skip-load', action='store_true', help="Skip the database loading step (useful if PostgreSQL is not running)")
    parser.add_argument('--skip-ingest', action='store_true', help="Skip the ingestion step (useful if raw data already exists)")
    args = parser.parse_args()

    logger = setup_logging("orchestrator")
    logger.info("==================================================")
    logger.info("Starting YouTube Trending ETL Pipeline Orchestrator")
    logger.info("==================================================")
    
    start_time = time.time()
    step_times = {}
    
    # --- STEP 1: INGESTION ---
    if not args.skip_ingest:
        ingest_start = time.time()
        ingest_success = run_ingestion()
        ingest_duration = time.time() - ingest_start
        step_times['Ingestion'] = ingest_duration
        
        if not ingest_success:
            logger.error("ETL Pipeline failed during the INGESTION step. Aborting run.")
            sys.exit(1)
            
        logger.info(f"Ingestion step completed successfully in {ingest_duration:.2f} seconds.")
        logger.info("--------------------------------------------------")
    else:
        logger.info("SKIPPING ingestion step (--skip-ingest flag set).")
        logger.info("--------------------------------------------------")
    
    # --- STEP 2: TRANSFORMATION ---
    transform_start = time.time()
    transform_success = run_transformation()
    transform_duration = time.time() - transform_start
    step_times['Transformation'] = transform_duration
    
    if not transform_success:
        logger.error("ETL Pipeline failed during the TRANSFORMATION step. Aborting run.")
        sys.exit(1)
        
    logger.info(f"Transformation step completed successfully in {transform_duration:.2f} seconds.")
    logger.info("--------------------------------------------------")
    
    # --- STEP 3: DATABASE LOAD ---
    if not args.skip_load:
        load_start = time.time()
        load_success = run_loading()
        load_duration = time.time() - load_start
        step_times['Loading'] = load_duration
        
        if not load_success:
            logger.error("ETL Pipeline failed during the LOADING step. Aborting run.")
            sys.exit(1)
            
        logger.info(f"Loading step completed successfully in {load_duration:.2f} seconds.")
        logger.info("--------------------------------------------------")
    else:
        logger.info("SKIPPING database loading step (--skip-load flag set).")
        logger.info("--------------------------------------------------")
    
    # --- SUMMARY ---
    total_duration = time.time() - start_time
    logger.info("==================================================")
    logger.info("ETL PIPELINE RUN COMPLETED SUCCESSFULLY!")
    logger.info(f"Total time elapsed: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
    for step_name, duration in step_times.items():
        logger.info(f"  - {step_name:<16}: {duration:.2f}s")
    logger.info("==================================================")

if __name__ == "__main__":
    main()

