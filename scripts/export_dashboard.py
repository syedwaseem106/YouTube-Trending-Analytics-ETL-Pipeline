"""
Export Dashboard Analytics
--------------------------
Reads processed Parquet data and generates reporting-ready CSV files
in the dashboard/ directory for visualization and analysis.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from utils import load_config, setup_logging, get_project_root


def run_export():
    logger = setup_logging("export_dashboard")
    logger.info("Starting dashboard export...")

    config = load_config()
    project_root = get_project_root()
    processed_dir = project_root / config.get("processed_data_dir", "data/processed")
    dashboard_dir = project_root / "dashboard"
    dashboard_dir.mkdir(parents=True, exist_ok=True)

    # Load processed data
    logger.info("Reading processed Parquet files...")
    videos_df = pd.read_parquet(processed_dir / "trending_videos")
    categories_df = pd.read_parquet(processed_dir / "categories.parquet")

    # Join categories
    videos_df = videos_df.merge(categories_df, on="category_id", how="left")
    logger.info(f"Loaded {len(videos_df)} trending records with {len(categories_df)} categories.")

    # ---- REPORT 1: Top 50 Most Viewed Videos (all regions) ----
    top_videos = (
        videos_df
        .sort_values("views", ascending=False)
        .drop_duplicates(subset=["video_id"], keep="first")
        .head(50)[["video_id", "title", "channel_title", "category_title", "region",
                    "views", "likes", "dislikes", "comment_count", "engagement_rate",
                    "trending_date", "publish_time"]]
    )
    top_videos.to_csv(dashboard_dir / "top_50_most_viewed.csv", index=False)
    logger.info("Exported: top_50_most_viewed.csv")

    # ---- REPORT 2: Category Performance Summary ----
    category_stats = (
        videos_df
        .groupby("category_title")
        .agg(
            total_videos=("video_id", "nunique"),
            total_views=("views", "sum"),
            avg_views=("views", "mean"),
            avg_likes=("likes", "mean"),
            avg_engagement=("engagement_rate", "mean"),
            total_trending_entries=("video_id", "count")
        )
        .round(2)
        .sort_values("total_views", ascending=False)
        .reset_index()
    )
    category_stats.to_csv(dashboard_dir / "category_performance.csv", index=False)
    logger.info("Exported: category_performance.csv")

    # ---- REPORT 3: Regional Trending Summary ----
    region_stats = (
        videos_df
        .groupby("region")
        .agg(
            unique_videos=("video_id", "nunique"),
            total_views=("views", "sum"),
            avg_views=("views", "mean"),
            avg_engagement=("engagement_rate", "mean"),
            avg_likes=("likes", "mean"),
            avg_comment_count=("comment_count", "mean")
        )
        .round(2)
        .sort_values("total_views", ascending=False)
        .reset_index()
    )
    region_stats.to_csv(dashboard_dir / "regional_summary.csv", index=False)
    logger.info("Exported: regional_summary.csv")

    # ---- REPORT 4: Trending Day of Week Analysis ----
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_stats = (
        videos_df
        .groupby("trending_day")
        .agg(
            trending_count=("video_id", "count"),
            avg_views=("views", "mean"),
            avg_engagement=("engagement_rate", "mean")
        )
        .round(2)
        .reindex(day_order)
        .reset_index()
    )
    day_stats.to_csv(dashboard_dir / "trending_by_day.csv", index=False)
    logger.info("Exported: trending_by_day.csv")

    # ---- REPORT 5: Publish Hour Analysis ----
    hour_stats = (
        videos_df
        .groupby("publish_hour")
        .agg(
            video_count=("video_id", "count"),
            avg_views=("views", "mean"),
            avg_engagement=("engagement_rate", "mean")
        )
        .round(2)
        .sort_index()
        .reset_index()
    )
    hour_stats.to_csv(dashboard_dir / "publish_hour_analysis.csv", index=False)
    logger.info("Exported: publish_hour_analysis.csv")

    # ---- REPORT 6: Top 20 Channels by Total Views ----
    top_channels = (
        videos_df
        .groupby("channel_title")
        .agg(
            unique_videos=("video_id", "nunique"),
            total_views=("views", "sum"),
            total_likes=("likes", "sum"),
            avg_engagement=("engagement_rate", "mean"),
            trending_appearances=("video_id", "count")
        )
        .round(4)
        .sort_values("total_views", ascending=False)
        .head(20)
        .reset_index()
    )
    top_channels.to_csv(dashboard_dir / "top_20_channels.csv", index=False)
    logger.info("Exported: top_20_channels.csv")

    # ---- REPORT 7: Full dataset sample for dashboard ----
    # Export a manageable sample (first 5000 records per region) for dashboard tools
    sample_df = videos_df.groupby("region").head(5000)
    sample_df.to_csv(dashboard_dir / "dashboard_sample.csv", index=False)
    logger.info(f"Exported: dashboard_sample.csv ({len(sample_df)} records)")

    logger.info("==================================================")
    logger.info(f"Dashboard export complete! {7} reports saved to {dashboard_dir}")
    logger.info("==================================================")
    return True


if __name__ == "__main__":
    run_export()
