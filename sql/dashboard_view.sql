-- ==============================================================================
-- DASHBOARD VIEW: AN ANALYTICS-READY FLAT DATASET
-- ==============================================================================

-- Create a view that combines the fact table (youtube_trending_statistics) 
-- and category dimensions for direct consumption by BI tools (Tableau/Power BI)
CREATE OR REPLACE VIEW youtube_dashboard_view AS
SELECT 
    v.video_id,
    v.trending_date,
    v.region,
    v.title,
    v.channel_title,
    c.category_title,
    v.publish_time,
    v.views,
    v.likes,
    v.dislikes,
    v.comment_count,
    v.comments_disabled,
    v.ratings_disabled,
    v.video_error_or_removed,
    v.engagement_rate,
    v.trending_day,
    v.publish_hour
FROM 
    youtube_trending_statistics v
JOIN 
    youtube_categories c ON v.category_id = c.category_id;

-- Comment describing the view
COMMENT ON VIEW youtube_dashboard_view IS 'Flat view for BI dashboard integrations (Tableau/Power BI), combining trending metrics and category names.';
