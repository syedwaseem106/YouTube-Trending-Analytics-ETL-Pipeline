import os
import logging
from pathlib import Path
import pandas as pd
from sqlalchemy import (
    create_engine, MetaData, Table, Column, 
    Integer, String, Date, DateTime, Boolean, BIGINT, Float, ForeignKey, text, Text
)
from sqlalchemy.exc import OperationalError
from utils import load_config, setup_logging, get_project_root, get_db_engine

def create_database_if_not_exists(logger: logging.Logger):
    """
    Connects to the default 'postgres' database to check if the target 
    database exists. If it does not, creates the target database.
    """
    config = load_config()
    db_config = config.get("database", {})
    
    host = db_config.get("host", "localhost")
    port = db_config.get("port", 5432)
    user = db_config.get("user", "postgres")
    password = db_config.get("password", "postgres")
    dbname = db_config.get("dbname", "youtube_trending")
    
    # Establish connection to the default postgres database
    default_uri = f"postgresql://{user}:{password}@{host}:{port}/postgres"
    
    try:
        # We need isolation_level AUTOCOMMIT because CREATE DATABASE cannot run in a transaction block
        engine = create_engine(default_uri, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            # Check if target db exists
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{dbname}'"))
            exists = result.scalar()
            
            if not exists:
                logger.info(f"Database '{dbname}' does not exist. Creating database...")
                conn.execute(text(f"CREATE DATABASE {dbname}"))
                logger.info(f"Database '{dbname}' created successfully.")
            else:
                logger.info(f"Database '{dbname}' already exists.")
    except Exception as e:
        logger.error(f"Error checking/creating database '{dbname}': {e}")
        logger.warning("Proceeding, assuming database may already be accessible directly.")

def run_loading():
    """
    Reads processed Parquet datasets, creates database tables with SQLAlchemy definitions,
    and loads the cleaned datasets into PostgreSQL.
    """
    logger = setup_logging("load")
    logger.info("Starting database loading phase...")
    
    try:
        config = load_config()
        project_root = get_project_root()
        processed_dir = project_root / config.get("processed_data_dir", "data/processed")
        
        # 1. Ensure database exists
        create_database_if_not_exists(logger)
        
        # 2. Get DB Connection Engine
        engine = get_db_engine()
        
        # 3. Read processed Parquet files
        categories_parquet_path = processed_dir / "categories.parquet"
        videos_parquet_path = processed_dir / "trending_videos"
        
        if not categories_parquet_path.exists():
            logger.error(f"Categories parquet file not found at: {categories_parquet_path}")
            return False
        if not videos_parquet_path.exists():
            logger.error(f"Videos parquet directory not found at: {videos_parquet_path}")
            return False
            
        logger.info("Reading processed Parquet files...")
        categories_df = pd.read_parquet(categories_parquet_path)
        videos_df = pd.read_parquet(videos_parquet_path)
        
        logger.info(f"Loaded Parquet datasets: {len(categories_df)} categories, {len(videos_df)} trending records.")
        
        # 4. Define Database Schemas using SQLAlchemy Metadata
        metadata = MetaData()
        
        # Category Dimension Table DDL
        categories_table = Table(
            'youtube_categories', metadata,
            Column('category_id', Integer, primary_key=True),
            Column('category_title', String(100), nullable=False)
        )
        
        # Video Trending Fact/Statistics Table DDL
        # Composite primary key (video_id, trending_date, region) represents a unique trending event
        trending_table = Table(
            'youtube_trending_statistics', metadata,
            Column('video_id', String(50), primary_key=True),
            Column('trending_date', Date, primary_key=True),
            Column('region', String(10), primary_key=True),
            Column('title', String(255)),
            Column('channel_title', String(255)),
            Column('category_id', Integer, ForeignKey('youtube_categories.category_id'), nullable=False),
            Column('publish_time', DateTime),
            Column('tags', Text), # TEXT column type
            Column('views', BIGINT),
            Column('likes', BIGINT),
            Column('dislikes', BIGINT),
            Column('comment_count', BIGINT),
            Column('thumbnail_link', String(255)),
            Column('comments_disabled', Boolean),
            Column('ratings_disabled', Boolean),
            Column('video_error_or_removed', Boolean),
            Column('description', Text), # TEXT column type
            Column('engagement_rate', Float),
            Column('trending_day', String(15)),
            Column('publish_hour', Integer)
        )
        
        # 5. Recreate Tables
        logger.info("Dropping existing tables and creating new schemas...")
        metadata.drop_all(engine)
        metadata.create_all(engine)
        logger.info("Database schemas defined and created successfully.")
        
        # 6. Load data using pandas to_sql (bulk loading)
        # Load Categories first (parent table)
        logger.info("Loading data into 'youtube_categories'...")
        categories_df.to_sql(
            'youtube_categories', 
            con=engine, 
            if_exists='append', 
            index=False,
            method='multi', # optimized multi-row inserts
            chunksize=1000
        )
        logger.info("Loaded categories successfully.")
        
        # Load Trending Statistics (child table)
        logger.info("Loading data into 'youtube_trending_statistics'...")
        videos_df.to_sql(
            'youtube_trending_statistics', 
            con=engine, 
            if_exists='append', 
            index=False,
            chunksize=5000 # Larger chunksize for bulk loading fact table
        )
        logger.info("Loaded trending statistics successfully.")
        
        logger.info("Database loading phase completed successfully.")
        return True
        
    except Exception as e:
        logger.exception(f"Database loading failed with error: {e}")
        return False

if __name__ == "__main__":
    run_loading()
