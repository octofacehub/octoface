"""Utility functions for OctoFace CLI."""

import os
import json
import subprocess
import datetime
import requests
import time
from pathlib import Path
from rich.console import Console

console = Console()

def check_credentials():
    """
    Check if all required credentials are set.
    
    Returns:
        bool: True if all credentials are set, False otherwise.
    """
    all_credentials_valid = True
    
    # Check GitHub API token
    github_token = os.environ.get("GITHUB_API_TOKEN")
    if not github_token:
        console.print("[red]GitHub API token not found. Please set GITHUB_API_TOKEN environment variable.[/red]")
        console.print("[yellow]Example: export GITHUB_API_TOKEN=\"your-github-api-token\"[/yellow]")
        all_credentials_valid = False
    
    # Check w3cli installation
    try:
        result = subprocess.run(["w3", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            console.print("[red]w3cli not found. Please install it with: npm i --global @web3-storage/w3cli[/red]")
            all_credentials_valid = False
    except FileNotFoundError:
        console.print("[red]w3cli not found. Please install it with: npm i --global @web3-storage/w3cli[/red]")
        all_credentials_valid = False
    
    # Check w3cli login
    try:
        result = subprocess.run(["w3", "did"], capture_output=True, text=True)
        if result.returncode != 0 or "No space" in result.stdout:
            console.print("[red]Not logged in to web3.storage. Please follow these steps:[/red]")
            console.print("[yellow]1. Run: w3 login --email your.email@example.com[/yellow]")
            console.print("[yellow]2. Check your email and click the verification link[/yellow]")
            console.print("[yellow]3. Run: w3 space create my-octoface-space[/yellow]")
            console.print("[yellow]4. Run: w3 space use my-octoface-space[/yellow]")
            all_credentials_valid = False
    except Exception:
        console.print("[red]Error checking web3.storage login. Please follow these steps:[/red]")
        console.print("[yellow]1. Run: w3 login --email your.email@example.com[/yellow]")
        console.print("[yellow]2. Check your email and click the verification link[/yellow]")
        console.print("[yellow]3. Run: w3 space create my-octoface-space[/yellow]")
        console.print("[yellow]4. Run: w3 space use my-octoface-space[/yellow]")
        all_credentials_valid = False
    
    return all_credentials_valid


def get_github_username():
    """
    Get the GitHub username from the API token.
    
    Returns:
        str: GitHub username or None if not found.
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    if not github_token:
        return None
    
    try:
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        response = requests.get("https://api.github.com/user", headers=headers)
        response.raise_for_status()
        return response.json().get("login")
    except Exception:
        # Silently handle errors and return None
        return None


def import_datetime():
    """Import datetime module on demand."""
    import datetime
    return datetime


def generate_model_metadata(name, description, tags, cid, model_path=None):
    """
    Generate metadata for a model.
    
    Args:
        name (str): Name of the model
        description (str): Description of the model
        tags (list): List of tags
        cid (str): IPFS CID
        model_path (str, optional): Path to the model directory
        
    Returns:
        dict: Model metadata
    """
    # Get GitHub username
    github_username = get_github_username()
    if not github_username:
        console.print("[yellow]GitHub username not available, using 'anonymous'[/yellow]")
        github_username = "anonymous"
    
    # Get current UTC time
    current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Create metadata
    metadata = {
        "name": name,
        "description": description or "",
        "author": github_username,
        "tags": tags,
        "ipfs_cid": cid,
        "size_mb": 0,  # Will be updated when the model is actually processed
        "created_at": current_time,
    }
    
    # Calculate model size if path is provided
    if model_path:
        try:
            # Get total size of the model directory
            total_size = 0
            for path, dirs, files in os.walk(model_path):
                for file in files:
                    fp = os.path.join(path, file)
                    total_size += os.path.getsize(fp)
            
            # Convert to MB
            size_mb = total_size / (1024 * 1024)
            metadata["size_mb"] = round(size_mb, 2)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not calculate model size: {str(e)}[/yellow]")
    
    return metadata


def generate_readme(metadata, model_path=None):
    """
    Generate README.md content for a model.
    
    Args:
        metadata (dict): Model metadata
        model_path (str, optional): Path to the model directory
        
    Returns:
        str: README.md content
    """
    name = metadata.get("name", "Unknown Model")
    description = metadata.get("description", "")
    tags = metadata.get("tags", [])
    cid = metadata.get("ipfs_cid", "")
    github_username = metadata.get("author", "anonymous")
    
    readme = f"""# {name}

{description}

## Details

- **Author**: [{github_username}](https://github.com/{github_username})
- **IPFS CID**: `{cid}`

## Tags

{', '.join([f'`{tag}`' for tag in tags]) if tags else 'None'}

## How to use

### Download from IPFS

```bash
# Install IPFS CLI if needed
npm i --global @web3-storage/w3cli

# Download the model
w3 get {cid} -o ./models/{name.lower().replace(' ', '-')}
```

## Web links

- [View on IPFS Gateway](https://w3s.link/ipfs/{cid})
"""
    
    return readme


def create_pull_request(name, metadata, readme):
    """
    Create a pull request with the model files.
    
    This function is a high-level wrapper around the GitHub PR creation process.
    It handles all the steps needed to create a PR with the model files.
    
    Args:
        name (str): Name of the model
        metadata (dict): Model metadata
        readme (str): README content
        
    Returns:
        str: URL of the created PR or None on failure
    """
    try:
        # Check GitHub API token
        github_token = os.environ.get("GITHUB_API_TOKEN")
        if not github_token:
            console.print("[red]GitHub API token not found. Please set GITHUB_API_TOKEN environment variable.[/red]")
            return None
            
        # Get GitHub username
        github_username = get_github_username()
        if not github_username:
            console.print("[red]Failed to get GitHub username[/red]")
            return None
            
        # Create timestamp and model slug
        timestamp = int(time.time())
        model_name_slug = name.lower().replace(" ", "-")
        branch_name = f"add-model-{model_name_slug}-{timestamp}"
        
        # Import GitHub functions here to avoid circular imports
        from octoface.github import (
            has_push_access, check_repo_initialized, create_initial_commit,
            create_branch, create_file, update_model_map, create_pull_request as github_create_pr,
            get_or_create_fork, create_branch_in_fork, create_file_in_fork, 
            create_pull_request_from_fork, test_github_access
        )
        
        # Test GitHub API access
        if not test_github_access():
            console.print("[red]Failed to access GitHub API. Please check your token and internet connection.[/red]")
            return None
            
        # Check if user has push access
        has_push = has_push_access()
        
        # Import model tree generation function
        from octoface.uploader import generate_model_tree
        
        # Generate a simple model tree if path is available
        if "path" in metadata:
            model_tree = generate_model_tree(metadata["path"])
        else:
            model_tree = []
            
        # If user has push access, create PR directly
        if has_push:
            # Check if we need to create an initial commit
            if not check_repo_initialized():
                console.print("[yellow]Repository is empty. Creating initial commit...[/yellow]")
                if not create_initial_commit():
                    console.print("[red]Failed to create initial commit[/red]")
                    return None
                
            # Create a new branch
            branch_created = create_branch(branch_name, "main")
            if not branch_created:
                console.print("[red]Failed to create branch[/red]")
                return None
                
            # Create model directory structure
            model_dir = f"models/{github_username}/{model_name_slug}"
            
            # Create files in the new branch
            files_to_create = [
                {
                    "path": f"{model_dir}/README.md",
                    "content": readme,
                    "message": f"Add README for {name}"
                },
                {
                    "path": f"{model_dir}/metadata.json",
                    "content": json.dumps(metadata, indent=2),
                    "message": f"Add metadata for {name}"
                }
            ]
            
            # Add model tree if available
            if model_tree:
                files_to_create.append({
                    "path": f"{model_dir}/tree.json",
                    "content": json.dumps(model_tree, indent=2),
                    "message": f"Add file tree for {name}"
                })
                
            # Create each file
            for file_info in files_to_create:
                if not create_file(file_info["path"], file_info["content"], file_info["message"], branch_name):
                    console.print(f"[red]Failed to create file: {file_info['path']}[/red]")
                    return None
                    
            # Update the global model map
            if not update_model_map(metadata, github_username, model_name_slug, branch_name):
                console.print("[red]Failed to update model map[/red]")
                return None
                
            # Create PR
            pr_url = github_create_pr(
                branch_name,
                f"Add model: {name}",
                f"This PR adds the {name} model by @{github_username}.\n\n"
                f"Model description: {metadata['description']}\n\n"
                f"IPFS CID: `{metadata['ipfs_cid']}`"
            )
            
            return pr_url
        else:
            # For users without push access, use fork-based workflow
            console.print("[yellow]You don't have push access to the main repository.[/yellow]")
            console.print("[yellow]Creating a fork and PR on your behalf...[/yellow]")
            
            # Create a fork if it doesn't exist
            fork_exists, fork_url = get_or_create_fork()
            if not fork_exists:
                console.print("[red]Failed to create or access fork[/red]")
                return None
                
            console.print(f"[green]Using fork: {fork_url}[/green]")
            
            # Create a new branch in the fork
            branch_created = create_branch_in_fork(branch_name, github_username)
            if not branch_created:
                console.print("[red]Failed to create branch in fork[/red]")
                return None
                
            # Create model directory structure
            model_dir = f"models/{github_username}/{model_name_slug}"
            
            # Create files in the fork branch
            files_to_create = [
                {
                    "path": f"{model_dir}/README.md",
                    "content": readme,
                    "message": f"Add README for {name}"
                },
                {
                    "path": f"{model_dir}/metadata.json",
                    "content": json.dumps(metadata, indent=2),
                    "message": f"Add metadata for {name}"
                }
            ]
            
            # Create each file in the fork
            for file_info in files_to_create:
                if not create_file_in_fork(file_info["path"], file_info["content"], file_info["message"], branch_name, github_username):
                    console.print(f"[red]Failed to create file in fork: {file_info['path']}[/red]")
                    return None
                    
            # Create PR from fork to main repo
            pr_url = create_pull_request_from_fork(
                branch_name,
                github_username,
                f"Add model: {name}",
                f"This PR adds the {name} model by @{github_username}.\n\n"
                f"Model description: {metadata['description']}\n\n"
                f"IPFS CID: `{metadata['ipfs_cid']}`"
            )
            
            return pr_url
    except Exception as e:
        console.print(f"[red]Error creating pull request: {str(e)}[/red]")
        return None 