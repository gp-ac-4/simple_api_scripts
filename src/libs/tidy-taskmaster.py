#!/usr/bin/env python3

import os
import time
import logging
from github import Github
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("workflow-queue")

# Constants for workflow states
ACTIVE_STATES = ["in_progress", "queued", "waiting", "pending", "action_required", "requested"]

def get_env_var(name, default=None, required=False):
    """Get environment variable or return default value."""
    value = os.environ.get(name, default)
    if required and value is None:
        raise ValueError(f"Environment variable {name} is required but not set")
    return value

def get_current_workflow_info():
    """Get information about the current workflow run."""
    return {
        "repo": get_env_var("GITHUB_REPOSITORY", required=True),
        "workflow_id": get_env_var("GITHUB_WORKFLOW", required=True),
        "run_id": int(get_env_var("GITHUB_RUN_ID", required=True)),
        "run_number": int(get_env_var("GITHUB_RUN_NUMBER", required=True)),
    }

def check_previous_workflow_runs(github_client, current_workflow):
    """
    Check for active workflow runs that started before the current one.
    """
    logger.info(f"Checking for previous workflow runs of {current_workflow['workflow_id']}")
    
    repo = github_client.get_repo(current_workflow["repo"])
    current_run = repo.get_workflow_run(current_workflow["run_id"])
    current_run_created_at = current_run.created_at
    
    # Get all workflow runs for the current workflow
    workflow = None
    for wf in repo.get_workflows():
        if wf.name == current_workflow["workflow_id"] or str(wf.id) == current_workflow["workflow_id"]:
            workflow = wf
            break
    
    if workflow is None:
        logger.error(f"Could not find workflow {current_workflow['workflow_id']}")
        return []
    
    # Find active runs that started before this one
    previous_active_runs = []
    for run in workflow.get_runs():
        # Skip the current run
        if run.id == current_workflow["run_id"]:
            continue
        
        # Only consider runs that started before the current one
        if run.created_at >= current_run_created_at:
            continue
        
        # Only consider active runs
        if run.status.lower() in ACTIVE_STATES:
            logger.info(f"Found active previous run: #{run.run_number} (ID: {run.id}, Status: {run.status})")
            previous_active_runs.append(run)
    
    return previous_active_runs

def wait_for_previous_runs(github_client, current_workflow, timeout_ms, delay_ms, incremental_backoff):
    """
    Wait for previous workflow runs to complete before proceeding.
    """
    start_time = datetime.now()
    timeout_seconds = timeout_ms / 1000
    delay_seconds = delay_ms / 1000
    
    logger.info(f"Starting wait with timeout of {timeout_seconds} seconds and delay of {delay_seconds} seconds")
    logger.info(f"Incremental backoff: {incremental_backoff}")
    
    while True:
        # Check elapsed time against timeout
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > timeout_seconds:
            logger.error(f"Timeout of {timeout_seconds} seconds exceeded after waiting for {elapsed:.2f} seconds")
            return False
        
        # Check for active previous runs
        previous_runs = check_previous_workflow_runs(github_client, current_workflow)
        
        if not previous_runs:
            logger.info("No previous workflow runs are active. Proceeding.")
            return True
        
        # Calculate remaining time
        remaining_seconds = timeout_seconds - elapsed
        logger.info(f"Found {len(previous_runs)} active previous runs. Waiting...")
        logger.info(f"Time elapsed: {elapsed:.2f}s, Remaining: {remaining_seconds:.2f}s")
        
        # Determine next delay time with consideration for backoff
        next_delay = delay_seconds
        if incremental_backoff:
            next_delay = min(delay_seconds * 2, remaining_seconds)
            delay_seconds = next_delay
        
        if next_delay >= remaining_seconds:
            next_delay = remaining_seconds
        
        logger.info(f"Waiting for {next_delay:.2f} seconds before checking again...")
        time.sleep(next_delay)

def main():
    # Get configuration from environment variables
    github_token = get_env_var("INPUT_GITHUB_TOKEN", required=True)
    timeout_ms = int(get_env_var("INPUT_TIMEOUT", "600000"))  # Default: 10 minutes
    delay_ms = int(get_env_var("INPUT_DELAY", "10000"))  # Default: 10 seconds
    incremental_backoff = get_env_var("INPUT_INCREMENTAL_BACKOFF", "true").lower() == "true"
    
    logger.info(f"Starting workflow queue action")
    logger.info(f"Timeout: {timeout_ms}ms, Delay: {delay_ms}ms, Incremental Backoff: {incremental_backoff}")
    
    # Initialize GitHub client
    github_client = Github(github_token)
    
    # Get current workflow information
    current_workflow = get_current_workflow_info()
    logger.info(f"Current workflow: {current_workflow['workflow_id']}, Run ID: {current_workflow['run_id']}")
    
    # Wait for previous workflow runs to complete
    success = wait_for_previous_runs(
        github_client,
        current_workflow,
        timeout_ms,
        delay_ms,
        incremental_backoff
    )
    
    if success:
        logger.info("Success: No previous workflow runs are active. Proceeding with the current run.")
        exit(0)
    else:
        logger.error("Failed: Timed out waiting for previous workflow runs to complete.")
        exit(1)

if __name__ == "__main__":
    main()