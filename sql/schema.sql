-- Schema Definition for YouTube Trending Analytics database
-- Database: youtube_trending

-- 1. Dimension Table: youtube_categories
-- Stores unique video category IDs and their names parsed from JSON
CREATE TABLE IF NOT EXISTS youtube_categories (
    category_id INT PRIMARY KEY,
    category_title VARCHAR(100) NOT NULL
);

-- 2. Fact/Timeseries Table: youtube_trending_statistics
-- Stores daily trending information for videos across regions
-- Composite Primary Key (video_id, trending_date, region) represents a unique trending event
CREATE TABLE IF NOT EXISTS youtube_trending_statistics (
    video_id VARCHAR(50),
    trending_date DATE,
    region VARCHAR(10),
    title VARCHAR(255),
    channel_title VARCHAR(255),
    category_id INT NOT NULL,
    publish_time TIMESTAMP,
    tags TEXT,
    views BIGINT,
    likes BIGINT,
    dislikes BIGINT,
    comment_count BIGINT,
    thumbnail_link VARCHAR(255),
    comments_disabled BOOLEAN,
    ratings_disabled BOOLEAN,
    video_error_or_removed BOOLEAN,
    description TEXT,
    engagement_rate DOUBLE PRECISION,
    trending_day VARCHAR(15),
    publish_hour INT,
    
    PRIMARY KEY (video_id, trending_date, region),
    FOREIGN KEY (category_id) REFERENCES youtube_categories(category_id)
);

-- Indexing for Query Performance Optimization
CREATE INDEX IF NOT EXISTS idx_trending_category_id ON youtube_trending_statistics(category_id);
CREATE INDEX IF NOT EXISTS idx_trending_region ON youtube_trending_statistics(region);
CREATE INDEX IF NOT EXISTS idx_trending_date ON youtube_trending_statistics(trending_date);
CREATE INDEX IF NOT EXISTS idx_trending_views ON youtube_trending_statistics(views DESC);
