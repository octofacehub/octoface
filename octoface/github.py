"""Module for GitHub API integration."""

import os
import json
import base64
import tempfile
from pathlib import Path
import requests
from rich.console import Console
import time

from octoface.utils import get_github_username
from octoface.uploader import generate_model_tree

console = Console()

# GitHub repository info
REPO_OWNER = "octofacehub"
REPO_NAME = "octofacehub.github.io"
API_BASE = "https://api.github.com"


def create_model_pr(model_name, description, tags, ipfs_cid, model_path):
    """
    Create a pull request to add a model to the OctoFaceHub.
    
    Args:
        model_name (str): Name of the model
        description (str): Description of the model
        tags (str): Comma-separated list of tags
        ipfs_cid (str): IPFS CID
        model_path (str): Path to model directory
        
    Returns:
        str: URL of the created PR or None on failure
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    if not github_token:
        console.print("[red]GitHub API token not found. Please set GITHUB_API_TOKEN environment variable.[/red]")
        console.print("[yellow]Example: export GITHUB_API_TOKEN=\"your-github-api-token\"[/yellow]")
        return None
    
    # Get GitHub username
    github_username = get_github_username()
    if not github_username:
        console.print("[red]Failed to get GitHub username[/red]")
        return None
    
    # Check if user has push access to the repository
    has_push = has_push_access()
    
    try:
        # Create a unique branch name with timestamp
        timestamp = int(time.time())
        model_name_slug = model_name.lower().replace(" ", "-")
        branch_name = f"add-model-{model_name_slug}-{timestamp}"
        
        # Import generate_model_metadata and generate_readme to avoid circular imports
        from octoface.utils import generate_model_metadata, generate_readme
        
        # Generate model metadata
        tags_list = [tag.strip() for tag in tags.split(",")] if isinstance(tags, str) else tags
        metadata = generate_model_metadata(model_name, description, tags_list, ipfs_cid, model_path)
        if not metadata:
            console.print("[red]Failed to generate model metadata[/red]")
            return None
        
        # Generate model tree
        model_tree = generate_model_tree(model_path)
        
        # Generate README
        readme_content = generate_readme(metadata, model_path)
        
        # If user has push access, create PR directly
        if has_push:
            try:
                # Check if we need to create an initial commit
                if not check_repo_initialized():
                    console.print("[yellow]Repository is empty. Creating initial commit...[/yellow]")
                    if not create_initial_commit():
                        console.print("[red]Failed to create initial commit[/red]")
                        return None
                
                # Use main as the default branch
                default_branch = "main"
                
                # Create a new branch
                branch_created = create_branch(branch_name, default_branch)
                if not branch_created:
                    console.print("[red]Failed to create branch[/red]")
                    return None
                
                # Create model directory structure using the GitHub username
                model_name_slug = model_name.lower().replace(" ", "-")
                model_dir = f"models/{github_username}/{model_name_slug}"
                
                # Create files in the new branch
                files_to_create = [
                    {
                        "path": f"{model_dir}/README.md",
                        "content": readme_content,
                        "message": f"Add README for {model_name}"
                    },
                    {
                        "path": f"{model_dir}/metadata.json",
                        "content": json.dumps(metadata, indent=2),
                        "message": f"Add metadata for {model_name}"
                    },
                    {
                        "path": f"{model_dir}/tree.json",
                        "content": json.dumps(model_tree, indent=2),
                        "message": f"Add file tree for {model_name}"
                    }
                ]
                
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
                pr_url = create_pull_request(
                    branch_name,
                    f"Add model: {model_name}",
                    f"This PR adds the {model_name} model by @{github_username}.\n\n"
                    f"Model description: {description or 'No description provided'}\n\n"
                    f"IPFS CID: `{ipfs_cid}`"
                )
                
                if pr_url:
                    console.print(f"[green]Successfully created PR: {pr_url}[/green]")
                    return pr_url
                else:
                    console.print("[red]Failed to create PR[/red]")
                    return None
            
            except Exception as e:
                console.print(f"[red]Error creating PR: {str(e)}[/red]")
                return None
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
                    "content": readme_content,
                    "message": f"Add README for {model_name}"
                },
                {
                    "path": f"{model_dir}/metadata.json",
                    "content": json.dumps(metadata, indent=2),
                    "message": f"Add metadata for {model_name}"
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
                f"Add model: {model_name}",
                f"This PR adds the {model_name} model by @{github_username}.\n\n"
                f"Model description: {description or 'No description provided'}\n\n"
                f"IPFS CID: `{ipfs_cid}`"
            )
            
            if pr_url:
                console.print(f"[green]Successfully created PR from your fork: {pr_url}[/green]")
                return pr_url
            else:
                console.print("[red]Failed to create PR from fork[/red]")
                return None
    
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return None


def get_or_create_fork():
    """
    Get or create a fork of the repository.
    
    Returns:
        tuple: (bool, str) indicating success and fork URL
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # Check if fork already exists
        response = requests.get(
            f"{API_BASE}/repos/{get_github_username()}/{REPO_NAME}",
            headers=headers
        )
        
        if response.status_code == 200:
            # Fork already exists
            console.print("[green]Using existing fork[/green]")
            return True, response.json().get("html_url")
        
        # Create a new fork
        console.print("[yellow]Creating a new fork...[/yellow]")
        response = requests.post(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/forks",
            headers=headers
        )
        
        if response.status_code in [200, 201, 202]:
            console.print("[green]Fork created successfully[/green]")
            return True, response.json().get("html_url")
        else:
            console.print(f"[red]Error creating fork: {response.status_code} {response.text}[/red]")
            return False, None
            
    except Exception as e:
        console.print(f"[red]Error checking/creating fork: {str(e)}[/red]")
        return False, None


def create_branch_in_fork(branch_name, github_username):
    """
    Create a new branch in the user's fork.
    
    Args:
        branch_name (str): Name of the new branch
        github_username (str): GitHub username
        
    Returns:
        bool: True if successful, False otherwise
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # Get the SHA of the latest commit on the main branch of the fork
        response = requests.get(
            f"{API_BASE}/repos/{github_username}/{REPO_NAME}/git/refs/heads/main",
            headers=headers
        )
        
        if response.status_code != 200:
            # Wait a bit for the fork to be ready (GitHub may need time)
            console.print("[yellow]Waiting for fork to be ready...[/yellow]")
            time.sleep(5)
            
            # Try again
            response = requests.get(
                f"{API_BASE}/repos/{github_username}/{REPO_NAME}/git/refs/heads/main",
                headers=headers
            )
        
        if response.status_code == 200:
            base_sha = response.json().get("object", {}).get("sha")
            
            if not base_sha:
                console.print("[red]Failed to get base branch SHA[/red]")
                return False
            
            # Create the new branch
            data = {
                "ref": f"refs/heads/{branch_name}",
                "sha": base_sha
            }
            
            response = requests.post(
                f"{API_BASE}/repos/{github_username}/{REPO_NAME}/git/refs",
                headers=headers,
                json=data
            )
            
            if response.status_code in [200, 201, 422]:  # 422 means branch already exists
                console.print(f"[green]Successfully created branch in fork: {branch_name}[/green]")
                return True
            else:
                console.print(f"[red]Error creating branch in fork: {response.status_code} {response.text}[/red]")
                return False
        else:
            console.print(f"[red]Failed to get base branch from fork. Status: {response.status_code}[/red]")
            console.print(f"[red]Response: {response.text}[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]Error creating branch in fork: {str(e)}[/red]")
        return False


def create_file_in_fork(path, content, commit_message, branch, github_username):
    """
    Create a file in the user's fork.
    
    Args:
        path (str): Path to the file in the repository
        content (str): File content
        commit_message (str): Commit message
        branch (str): Branch to create the file in
        github_username (str): GitHub username
        
    Returns:
        bool: True if successful, False otherwise
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # Check if file already exists in fork
        check_response = requests.get(
            f"{API_BASE}/repos/{github_username}/{REPO_NAME}/contents/{path}?ref={branch}",
            headers=headers
        )
        
        if check_response.status_code == 200:
            # File already exists, need to update it with a SHA
            file_sha = check_response.json().get("sha")
            
            # Update the file
            data = {
                "message": commit_message,
                "content": base64.b64encode(content.encode()).decode(),
                "branch": branch,
                "sha": file_sha
            }
        else:
            # Create new file
            data = {
                "message": commit_message,
                "content": base64.b64encode(content.encode()).decode(),
                "branch": branch
            }
        
        response = requests.put(
            f"{API_BASE}/repos/{github_username}/{REPO_NAME}/contents/{path}",
            headers=headers,
            json=data
        )
        
        if response.status_code in [200, 201]:
            console.print(f"[green]Successfully created/updated file in fork: {path}[/green]")
            return True
        else:
            console.print(f"[red]Error creating file in fork: {response.status_code} {response.text}[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]Error creating file in fork: {str(e)}[/red]")
        return False


def create_pull_request_from_fork(branch, github_username, title, body):
    """
    Create a pull request from a fork.
    
    Args:
        branch (str): Branch to create PR from
        github_username (str): GitHub username
        title (str): PR title
        body (str): PR body
        
    Returns:
        str: URL of the created PR or None on failure
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        data = {
            "title": title,
            "body": body,
            "head": f"{github_username}:{branch}",
            "base": "main"
        }
        
        response = requests.post(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/pulls",
            headers=headers,
            json=data
        )
        
        if response.status_code == 201:
            pr_data = response.json()
            pr_url = pr_data.get("html_url")
            console.print(f"[green]Successfully created PR from fork: {pr_url}[/green]")
            return pr_url
        else:
            console.print(f"[red]Error creating PR from fork: {response.status_code} {response.text}[/red]")
            return None
            
    except Exception as e:
        console.print(f"[red]Error creating PR from fork: {str(e)}[/red]")
        return None


def check_repo_initialized():
    """
    Check if the repository has been initialized with at least one commit.
    
    Returns:
        bool: True if initialized, False otherwise
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # Try to get the main branch
        response = requests.get(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/branches/main",
            headers=headers
        )
        
        return response.status_code == 200
    
    except Exception as e:
        console.print(f"[red]Error checking if repo is initialized: {str(e)}[/red]")
        return False


def create_initial_commit():
    """
    Create an initial commit in the repository.
    
    Returns:
        bool: True if successful, False otherwise
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # Create a README.md file in the main branch
        readme_content = """# OctoFaceHub

A catalog of IPFS-hosted models for OctoFace.

## About

OctoFaceHub is a hub for discovering and sharing models that can be used with OctoFace.
Models are stored on IPFS, making them decentralized and accessible from anywhere.

## Contributing

To contribute a model, use the OctoFace CLI:

```bash
# Install the CLI
pip install octoface

# Upload a model
octoface upload /path/to/model --name "My Model" --description "A description" --tags "tag1,tag2"
```

For more information, see the [OctoFace repository](https://github.com/octofacehub/octoface).
"""
        
        # Create the README file
        data = {
            "message": "Initial commit",
            "content": base64.b64encode(readme_content.encode()).decode()
        }
        
        response = requests.put(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/contents/README.md",
            headers=headers,
            json=data
        )
        
        if response.status_code in [200, 201]:
            console.print("[green]Successfully created initial commit[/green]")
            return True
        else:
            console.print(f"[red]Error creating initial commit: {response.status_code} {response.text}[/red]")
            return False
    
    except Exception as e:
        console.print(f"[red]Error creating initial commit: {str(e)}[/red]")
        return False


def create_branch(branch_name, base_branch):
    """
    Create a new branch.
    
    Args:
        branch_name (str): Name of the new branch
        base_branch (str): Base branch to create from
        
    Returns:
        bool: True if successful, False otherwise
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # Check if branch already exists
        check_response = requests.get(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/branches/{branch_name}",
            headers=headers
        )
        
        if check_response.status_code == 200:
            # Branch already exists, consider this a success
            console.print(f"[yellow]Branch {branch_name} already exists, reusing it.[/yellow]")
            return True
        
        # Get the SHA of the latest commit on the base branch
        response = requests.get(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/refs/heads/{base_branch}",
            headers=headers
        )
        
        if response.status_code == 200:
            base_sha = response.json().get("object", {}).get("sha")
            
            if not base_sha:
                console.print("[red]Failed to get base branch SHA[/red]")
                return False
            
            # Create the new branch
            data = {
                "ref": f"refs/heads/{branch_name}",
                "sha": base_sha
            }
            
            response = requests.post(
                f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/refs",
                headers=headers,
                json=data
            )
            
            if response.status_code == 201:
                console.print(f"[green]Successfully created branch: {branch_name}[/green]")
                return True
            elif response.status_code == 409:  # Conflict - branch already exists
                console.print(f"[yellow]Branch {branch_name} already exists, reusing it.[/yellow]")
                return True
            else:
                console.print(f"[red]Error creating branch: {response.status_code} {response.text}[/red]")
                return False
        else:
            console.print(f"[red]Failed to get base branch. Status: {response.status_code}[/red]")
            console.print(f"[red]Response: {response.text}[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]Error creating branch: {str(e)}[/red]")
        return False


def create_file(path, content, commit_message, branch):
    """
    Create a file in the repository.
    
    Args:
        path (str): Path to the file in the repository
        content (str): File content
        commit_message (str): Commit message
        branch (str): Branch to create the file in
        
    Returns:
        bool: True if successful, False otherwise
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # Check if file already exists
        check_response = requests.get(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}?ref={branch}",
            headers=headers
        )
        
        if check_response.status_code == 200:
            # File already exists, need to update it with a SHA
            file_sha = check_response.json().get("sha")
            
            # Update the file
            data = {
                "message": commit_message,
                "content": base64.b64encode(content.encode()).decode(),
                "branch": branch,
                "sha": file_sha
            }
        else:
            # Create new file
            data = {
                "message": commit_message,
                "content": base64.b64encode(content.encode()).decode(),
                "branch": branch
            }
        
        response = requests.put(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}",
            headers=headers,
            json=data
        )
        
        if response.status_code in [200, 201]:
            console.print(f"[green]Successfully created/updated file: {path}[/green]")
            return True
        else:
            console.print(f"[red]Error creating file: {response.status_code} {response.text}[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]Error creating file: {str(e)}[/red]")
        return False


def update_model_map(metadata, github_username, model_name, branch):
    """
    Update the global model map.
    
    Args:
        metadata (dict): Model metadata
        github_username (str): GitHub username
        model_name (str): Model name (slug format)
        branch (str): Branch to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # Get the current model map if it exists
        model_map_path = "models/model-map.json"
        response = requests.get(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{model_map_path}?ref={branch}",
            headers=headers
        )
        
        if response.status_code == 200:
            # Model map exists, get its content and SHA
            model_map_data = response.json()
            model_map_content = base64.b64decode(model_map_data.get("content")).decode("utf-8")
            model_map_sha = model_map_data.get("sha")
            
            try:
                model_map = json.loads(model_map_content)
            except json.JSONDecodeError:
                console.print("[red]Error: model map is not valid JSON[/red]")
                model_map = {"models": []}
        else:
            # Model map doesn't exist, create it
            model_map = {"models": []}
            model_map_sha = None
        
        # Add the new model to the model map
        model_entry = {
            "name": metadata["name"],
            "author": metadata["author"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "ipfs_cid": metadata["ipfs_cid"],
            "size_mb": metadata["size_mb"],
            "created_at": metadata["created_at"],
            "path": f"models/{github_username}/{model_name}"
        }
        
        # Check if model already exists in the map
        exists = False
        for i, model in enumerate(model_map["models"]):
            model_path = model.get("path", "")
            if model_path == model_entry["path"]:
                # Update the existing entry
                model_map["models"][i] = model_entry
                exists = True
                break
        
        if not exists:
            # Add the new model entry
            model_map["models"].append(model_entry)
        
        # Prepare data for update
        updated_content = json.dumps(model_map, indent=2)
        
        data = {
            "message": f"Update model map with {metadata['name']}",
            "content": base64.b64encode(updated_content.encode()).decode(),
            "branch": branch
        }
        
        if model_map_sha:
            data["sha"] = model_map_sha
        
        # Update the model map file
        response = requests.put(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/contents/{model_map_path}",
            headers=headers,
            json=data
        )
        
        if response.status_code in [200, 201]:
            console.print(f"[green]Successfully updated model map[/green]")
            return True
        else:
            console.print(f"[red]Error updating model map: {response.status_code} {response.text}[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]Error updating model map: {str(e)}[/red]")
        return False


def create_pull_request(branch, title, body):
    """
    Create a pull request.
    
    Args:
        branch (str): Branch to create PR from
        title (str): PR title
        body (str): PR body
        
    Returns:
        str: URL of the created PR or None on failure
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        data = {
            "title": title,
            "body": body,
            "head": branch,
            "base": "main"
        }
        
        response = requests.post(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/pulls",
            headers=headers,
            json=data
        )
        
        if response.status_code == 201:
            pr_data = response.json()
            pr_url = pr_data.get("html_url")
            console.print(f"[green]Successfully created PR: {pr_url}[/green]")
            return pr_url
        else:
            console.print(f"[red]Error creating PR: {response.status_code} {response.text}[/red]")
            return None
            
    except Exception as e:
        console.print(f"[red]Error creating PR: {str(e)}[/red]")
        return None


def test_github_access():
    """
    Test GitHub API access.
    
    Returns:
        bool: True if successful, False otherwise
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    if not github_token:
        console.print("[red]GitHub API token not found. Please set GITHUB_API_TOKEN environment variable.[/red]")
        return False
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        # Test API access by getting user info
        response = requests.get(
            f"{API_BASE}/user",
            headers=headers
        )
        
        if response.status_code == 200:
            user_data = response.json()
            console.print(f"[green]Successfully connected to GitHub as: {user_data.get('login')}[/green]")
            
            # Test repository access
            repo_response = requests.get(
                f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}",
                headers=headers
            )
            
            if repo_response.status_code == 200:
                console.print(f"[green]Successfully accessed repository: {REPO_OWNER}/{REPO_NAME}[/green]")
                return True
            else:
                console.print(f"[red]Failed to access repository: {REPO_OWNER}/{REPO_NAME}[/red]")
                console.print(f"[red]Status code: {repo_response.status_code}[/red]")
                console.print(f"[red]Response: {repo_response.text}[/red]")
                return False
        else:
            console.print(f"[red]Failed to authenticate with GitHub API. Status code: {response.status_code}[/red]")
            console.print(f"[red]Response: {response.text}[/red]")
            return False
    
    except Exception as e:
        console.print(f"[red]Error testing GitHub access: {str(e)}[/red]")
        return False


def has_push_access():
    """
    Check if the user has push access to the repository.
    
    Returns:
        bool: True if the user has push access, False otherwise
    """
    github_token = os.environ.get("GITHUB_API_TOKEN")
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}",
            headers=headers
        )
        
        if response.status_code == 200:
            permissions = response.json().get("permissions", {})
            return permissions.get("push", False) or permissions.get("admin", False)
        
        return False
    
    except Exception:
        return False 