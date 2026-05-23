import os
import json
import shutil
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from utils import load_config, setup_logging, get_project_root

def read_csv_safe(file_path: Path) -> pd.DataFrame:
    """Reads a CSV file, attempting multiple encodings to handle special characters."""
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            return df
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise e
            
    # Final fallback: read with 'replace' error handler for decode issues
    return pd.read_csv(file_path, encoding='utf-8', errors='replace')

def parse_categories(raw_dir: Path, regions: list, logger: logging.Logger) -> pd.DataFrame:
    """
    Parses region-specific JSON files to extract category mappings.
    Returns a unified category DataFrame with columns: [category_id, category_title]
    """
    category_map = {}
    
    for region in regions:
        json_path = raw_dir / f"{region}_category_id.json"
        if not json_path.exists():
            logger.warning(f"Category JSON not found for region {region}: {json_path}")
            continue
            
        logger.info(f"Parsing categories from {json_path.name}...")
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for item in data.get("items", []):
                cat_id = int(item["id"])
                cat_title = item["snippet"]["title"]
                category_map[cat_id] = cat_title
        except Exception as e:
            logger.error(f"Error parsing JSON file {json_path.name}: {e}")
            
    # Convert map to DataFrame
    categories_df = pd.DataFrame(
        list(category_map.items()), 
        columns=['category_id', 'category_title']
    )
    # Deduplicate categories
    categories_df.drop_duplicates(subset=['category_id'], inplace=True)
    logger.info(f"Parsed {len(categories_df)} unique video categories.")
    return categories_df

def run_transformation():
    """
    Reads raw CSV data, cleans and validates it, generates derived columns,
    joins category titles, and writes the output as partitioned Parquet files.
    """
    logger = setup_logging("transform")
    logger.info("Starting transformation phase...")
    
    try:
        config = load_config()
        project_root = get_project_root()
        
        raw_dir = project_root / config.get("raw_data_dir", "data/raw")
        processed_dir = project_root / config.get("processed_data_dir", "data/processed")
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        regions = config.get("regions", ["US", "CA", "GB", "IN", "DE", "FR"])
        
        # 1. Parse category JSONs
        categories_df = parse_categories(raw_dir, regions, logger)
        if categories_df.empty:
            logger.error("No category mapping could be parsed. Transformation aborted.")
            return False
            
        # Save categories as Parquet
        categories_path = processed_dir / "categories.parquet"
        categories_df.to_parquet(categories_path, index=False)
        logger.info(f"Saved category dimensions to {categories_path}")
        
        # 2. Process regional trending CSVs
        dfs = []
        for region in regions:
            csv_path = raw_dir / f"{region}videos.csv"
            if not csv_path.exists():
                logger.warning(f"Raw CSV not found for region {region}: {csv_path}")
                continue
                
            logger.info(f"Loading raw data for region: {region}...")
            df = read_csv_safe(csv_path)
            
            # Add regional descriptor
            df['region'] = region
            dfs.append(df)
            logger.info(f"Loaded {len(df)} records for region {region}.")
            
        if not dfs:
            logger.error("No regional dataframes were loaded. Transformation aborted.")
            return False
            
        # Combine all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
        logger.info(f"Combined dataframe size: {len(combined_df)} records.")
        
        # 3. Standardize Columns to Lowercase
        combined_df.columns = combined_df.columns.str.lower()
        
        # 4. Data Cleaning & Normalization
        # Fill Null Values
        combined_df['description'] = combined_df['description'].fillna('No description provided')
        combined_df['tags'] = combined_df['tags'].fillna('[none]')
        
        # Convert publish_time to datetime
        logger.info("Converting publish_time and trending_date to datetime formats...")
        combined_df['publish_time'] = pd.to_datetime(combined_df['publish_time'], errors='coerce')
        
        # Parse trending_date (typically in 'YY.DD.MM' format in this dataset)
        # We try '%y.%d.%m' first, and fallback to generic parsing if it fails
        try:
            combined_df['trending_date'] = pd.to_datetime(combined_df['trending_date'], format='%y.%d.%m', errors='coerce')
        except Exception:
            logger.warning("Failed parsing trending_date with '%y.%d.%m', falling back to automatic parsing...")
            combined_df['trending_date'] = pd.to_datetime(combined_df['trending_date'], errors='coerce')
            
        # Drop rows with critical null fields (dates must be valid)
        initial_count = len(combined_df)
        combined_df = combined_df.dropna(subset=['publish_time', 'trending_date', 'category_id'])
        dropped_null_dates = initial_count - len(combined_df)
        if dropped_null_dates > 0:
            logger.info(f"Dropped {dropped_null_dates} rows due to invalid/null dates or category IDs.")
            
        # Cast category_id to integer
        combined_df['category_id'] = combined_df['category_id'].astype(int)
            
        # Deduplication
        # Remove exact duplicate rows
        combined_df.drop_duplicates(inplace=True)
        
        # A video can only have one trending entry per day per region. 
        # If there are duplicate trending records for the same video/date/region, keep the one with the maximum views.
        combined_df = combined_df.sort_values(by='views', ascending=False)
        combined_df.drop_duplicates(subset=['video_id', 'trending_date', 'region'], keep='first', inplace=True)
        
        deduped_count = len(combined_df)
        logger.info(f"Deduplication complete. Remaining records: {deduped_count} (Dropped {initial_count - deduped_count} duplicates/nulls).")
        
        # 5. Feature Engineering (Derived Columns)
        logger.info("Performing feature engineering...")
        
        # Engagement rate: (likes + dislikes + comment_count) / views
        # Use np.where to prevent division by zero or negative views
        total_interactions = combined_df['likes'].fillna(0) + combined_df['dislikes'].fillna(0) + combined_df['comment_count'].fillna(0)
        combined_df['engagement_rate'] = np.where(
            combined_df['views'] > 0,
            total_interactions / combined_df['views'],
            0.0
        )
        # Format engagement_rate to 4 decimal places
        combined_df['engagement_rate'] = combined_df['engagement_rate'].round(4)
        
        # Trending day of the week
        combined_df['trending_day'] = combined_df['trending_date'].dt.day_name()
        
        # Publish hour
        combined_df['publish_hour'] = combined_df['publish_time'].dt.hour
        
        # 6. Data Validation Checks
        # Validate that views, likes, dislikes, comment_count are >= 0
        invalid_metrics = combined_df[
            (combined_df['views'] < 0) | 
            (combined_df['likes'] < 0) | 
            (combined_df['dislikes'] < 0) | 
            (combined_df['comment_count'] < 0)
        ]
        if not invalid_metrics.empty:
            logger.warning(f"Found {len(invalid_metrics)} rows with negative engagement metrics. Setting metrics to 0.")
            for col in ['views', 'likes', 'dislikes', 'comment_count']:
                combined_df[col] = combined_df[col].clip(lower=0)
                
        # 7. Write clean dataset as Partitioned Parquet
        logger.info("Writing processed data to partitioned Parquet files...")
        
        # Define output directory for trending statistics
        statistics_parquet_dir = processed_dir / "trending_videos"
        
        # If directory already exists, clear it to avoid stale partitions
        if statistics_parquet_dir.exists():
            shutil.rmtree(statistics_parquet_dir)
            
        combined_df.to_parquet(
            statistics_parquet_dir,
            index=False,
            partition_cols=['region'],
            engine='pyarrow'
        )
        logger.info(f"Transformation complete. Partitioned dataset saved to: {statistics_parquet_dir}")
        return True
        
    except Exception as e:
        logger.exception(f"Transformation failed with error: {e}")
        return False

if __name__ == "__main__":
    run_transformation()
