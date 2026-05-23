from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

# Default arguments for the Airflow tasks
default_args = {
    'owner': 'data_engineering_team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
with DAG(
    'youtube_trending_etl_pipeline',
    default_args=default_args,
    description='A daily batch ETL pipeline for processing YouTube trending video data',
    schedule_interval='0 2 * * *',  # Runs daily at 2:00 AM UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['youtube', 'etl', 'pandas', 'postgres'],
) as dag:

    # 1. Start Task
    start_task = EmptyOperator(
        task_id='start_pipeline'
    )

    # 2. Run ETL script Task using BashOperator
    # Assumes the code is mounted or deployed to /opt/airflow/dags/youtube_etl
    run_etl_pipeline = BashOperator(
        task_id='run_youtube_etl',
        bash_command='python /opt/airflow/dags/youtube_etl/scripts/run_pipeline.py',
        env={
            'PYTHONPATH': '/opt/airflow/dags/youtube_etl/scripts',
        }
    )

    # 3. End Task
    end_task = EmptyOperator(
        task_id='end_pipeline'
    )

    # Task Dependencies
    start_task >> run_etl_pipeline >> end_task
