-- ==============================================================================
-- ANALYTICAL SQL QUERIES: YOUTUBE TRENDING VIDEOS
-- ==============================================================================

-- 1. Top Viewed Categories
-- Goal: Find which video categories generate the most views globally and per region.
-- This query uses a CTE and ROW_NUMBER() window function to find the top 3 categories per region.
WITH regional_category_views AS (
    SELECT 
        v.region,
        c.category_title,
        SUM(v.views) AS total_views,
        COUNT(DISTINCT v.video_id) AS unique_videos_count,
        RANK() OVER (PARTITION BY v.region ORDER BY SUM(v.views) DESC) as category_rank
    FROM 
        youtube_trending_statistics v
    JOIN 
        youtube_categories c ON v.category_id = c.category_id
    GROUP BY 
        v.region, 
        c.category_title
)
SELECT 
    region,
    category_rank,
    category_title,
    total_views,
    unique_videos_count
FROM 
    regional_category_views
WHERE 
    category_rank <= 3
ORDER BY 
    region ASC, 
    category_rank ASC;


-- 2. Most Liked Channels
-- Goal: Identify the top 10 channels with the most cumulative likes across all regions.
-- Since the same video can trend multiple days, we take the MAX likes per video to avoid over-counting,
-- and then sum those up by channel.
WITH max_likes_per_video AS (
    SELECT 
        channel_title,
        video_id,
        MAX(likes) as max_likes
    FROM 
        youtube_trending_statistics
    GROUP BY 
        channel_title, 
        video_id
)
SELECT 
    channel_title,
    SUM(max_likes) AS total_accumulated_likes,
    COUNT(video_id) AS number_of_trending_videos
FROM 
    max_likes_per_video
GROUP BY 
    channel_title
ORDER BY 
    total_accumulated_likes DESC
LIMIT 10;


-- 3. Region-wise Trending Analysis
-- Goal: Analyze key metrics (views, engagement, likes-to-dislikes ratio) across different regions.
SELECT 
    region,
    COUNT(DISTINCT video_id) AS total_unique_trending_videos,
    SUM(views) AS total_views,
    ROUND(AVG(engagement_rate)::numeric * 100, 2) AS average_engagement_percentage,
    SUM(likes) AS total_likes,
    SUM(dislikes) AS total_dislikes,
    -- Handle division by zero for dislikes
    ROUND((SUM(likes)::numeric / NULLIF(SUM(dislikes), 0)), 2) AS likes_to_dislikes_ratio
FROM 
    youtube_trending_statistics
GROUP BY 
    region
ORDER BY 
    total_views DESC;


-- 4. Videos with Highest Engagement Rate
-- Goal: Find the top 10 most engaging individual videos.
-- We filter out videos with less than 100,000 views to ensure we look at widely viewed content rather than outliers.
WITH unique_videos_latest_state AS (
    -- Get the record of the day when the video reached its peak views
    SELECT 
        video_id,
        title,
        channel_title,
        region,
        views,
        likes,
        dislikes,
        comment_count,
        engagement_rate,
        ROW_NUMBER() OVER (PARTITION BY video_id, region ORDER BY views DESC) as rn
    FROM 
        youtube_trending_statistics
    WHERE 
        views >= 100000
)
SELECT 
    title,
    channel_title,
    region,
    views,
    engagement_rate,
    (likes + dislikes + comment_count) as total_interactions
FROM 
    unique_videos_latest_state
WHERE 
    rn = 1
ORDER BY 
    engagement_rate DESC
LIMIT 10;


-- 5. Daily Trending Patterns
-- Goal: Analyze if certain days of the week have more video updates or higher viewership.
SELECT 
    trending_day,
    COUNT(*) AS total_trending_records,
    ROUND(AVG(views), 2) AS average_views_per_record,
    SUM(views) AS total_views_on_day
FROM 
    youtube_trending_statistics
GROUP BY 
    trending_day
ORDER BY 
    -- Custom sorting order to output Monday -> Sunday
    CASE trending_day
        WHEN 'Monday' THEN 1
        WHEN 'Tuesday' THEN 2
        WHEN 'Wednesday' THEN 3
        WHEN 'Thursday' THEN 4
        WHEN 'Friday' THEN 5
        WHEN 'Saturday' THEN 6
        WHEN 'Sunday' THEN 7
        ELSE 8
    END;
