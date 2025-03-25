"""Utility functions for OctoFace CLI."""

import os
import json
import subprocess
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
    import requests
    
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


def generate_model_metadata(name, description, tags, cid):
    """
    Generate metadata for a model.
    
    Args:
        name (str): Name of the model
        description (str): Description of the model
        tags (list): List of tags
        cid (str): IPFS CID
        
    Returns:
        dict: Model metadata
    """
    # Get GitHub username
    github_username = get_github_username()
    if not github_username:
        console.print("[yellow]GitHub username not available, using 'anonymous'[/yellow]")
        github_username = "anonymous"
    
    # Get current UTC time
    import datetime
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
    
    return metadata


def generate_readme(name, description, tags, cid):
    """
    Generate README.md content for a model.
    
    Args:
        name (str): Name of the model
        description (str): Description of the model
        tags (list): List of tags
        cid (str): IPFS CID
        
    Returns:
        str: README.md content
    """
    # Get GitHub username
    github_username = get_github_username()
    if not github_username:
        github_username = "anonymous"
    
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