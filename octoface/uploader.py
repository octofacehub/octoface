"""Module for uploading models to IPFS using web3.storage."""

import os
import subprocess
import tempfile
from pathlib import Path
from rich.console import Console

console = Console()

def upload_to_ipfs(model_path):
    """
    Upload a model to IPFS using web3.storage.
    
    Args:
        model_path (str): Path to the model directory
        
    Returns:
        str: IPFS CID or None on failure
    """
    try:
        # Check if path exists
        if not os.path.exists(model_path):
            console.print(f"[red]Path does not exist: {model_path}[/red]")
            return None
        
        model_path = os.path.abspath(model_path)
        console.print(f"[yellow]Uploading model from: {model_path}[/yellow]")
        
        # First check if we're logged in
        try:
            whoami_result = subprocess.run(
                ["w3", "whoami"],
                capture_output=True,
                text=True
            )
            
            if whoami_result.returncode != 0:
                console.print("[red]Not logged in to web3.storage. Please login first.[/red]")
                console.print("[yellow]Run: w3 login --email your.email@example.com[/yellow]")
                return None
            
            # Check if space is selected
            space_result = subprocess.run(
                ["w3", "space", "ls"],
                capture_output=True,
                text=True
            )
            
            if space_result.returncode != 0 or "*" not in space_result.stdout:
                console.print("[red]No space selected. Please select a space first.[/red]")
                console.print("[yellow]Run: w3 space use <your-space-name>[/yellow]")
                console.print("[yellow]Available spaces:[/yellow]")
                console.print(space_result.stdout)
                return None
            
            # Space is selected, proceed with upload
            console.print("[yellow]Running: w3 up[/yellow]")
            
            # Run w3 up command
            up_result = subprocess.run(
                ["w3", "up", model_path],
                capture_output=True,
                text=True
            )
            
            if up_result.returncode != 0:
                console.print(f"[red]Error running w3 up: {up_result.stderr}[/red]")
                return None
            
            # Parse CID from output
            output = up_result.stdout.strip()
            if not output:
                console.print("[red]Error: Empty output from w3 up command[/red]")
                return None
            
            # Look for a line containing 'ipfs/' followed by a CID
            import re
            cid_match = re.search(r'ipfs/([a-zA-Z0-9]+)', output)
            if cid_match:
                cid = cid_match.group(1)
                console.print(f"[green]Successfully uploaded to IPFS with CID: {cid}[/green]")
                console.print(f"[green]Access at: https://w3s.link/ipfs/{cid}[/green]")
                return cid
            
            # If we can't find the CID using regex, just use the last line
            lines = output.strip().split("\n")
            for line in reversed(lines):
                line = line.strip()
                if line and not line.startswith("⁂") and "https:" not in line:
                    cid = line
                    console.print(f"[green]Successfully uploaded to IPFS with CID: {cid}[/green]")
                    console.print(f"[green]Access at: https://w3s.link/ipfs/{cid}[/green]")
                    return cid
            
            # As a last resort, extract from the URL
            for line in reversed(lines):
                if "https://w3s.link/ipfs/" in line:
                    cid = line.split("https://w3s.link/ipfs/")[1].strip()
                    console.print(f"[green]Successfully uploaded to IPFS with CID: {cid}[/green]")
                    console.print(f"[green]Access at: https://w3s.link/ipfs/{cid}[/green]")
                    return cid
            
            console.print("[red]Could not extract CID from output[/red]")
            console.print(f"[yellow]Raw output: {output}[/yellow]")
            return None
            
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error running w3 command: {e}[/red]")
            console.print(f"[red]stderr: {e.stderr}[/red]")
            return None
        
    except Exception as e:
        console.print(f"[red]Error uploading to IPFS: {str(e)}[/red]")
        return None


def generate_model_tree(name, metadata, readme):
    """
    Generate a tree representation of model files for OctoFaceHub.
    
    Args:
        name (str): Name of the model
        metadata (dict): Model metadata
        readme (str): README content
        
    Returns:
        dict: Tree structure of the model files
    """
    # Create a basic tree structure for a model
    return {
        "metadata.json": metadata,
        "README.md": readme
    }


def generate_model_tree_from_path(model_path):
    """
    Generate a tree representation of model files from a local directory.
    
    Args:
        model_path (str): Path to the model directory
        
    Returns:
        dict: Tree structure of the model
    """
    path = Path(model_path)
    
    # Check if path exists and is a directory
    if not path.exists() or not path.is_dir():
        return {}
    
    result = {
        "name": path.name,
        "type": "directory",
        "children": []
    }
    
    # Maximum file size to include in the tree (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # Process directory contents
    for item in sorted(path.iterdir()):
        if item.is_dir():
            # Recursively process subdirectories
            child = generate_model_tree_from_path(str(item))
            result["children"].append(child)
        else:
            # Get file size
            size = item.stat().st_size
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
            
            # Add file to tree
            result["children"].append({
                "name": item.name,
                "type": "file",
                "size": size_str,
                "size_bytes": size,
                # Only include content for small text files
                "content": get_file_preview(item) if should_preview_file(item, size) else None
            })
    
    return result


def should_preview_file(path, size):
    """
    Determine if a file should have a preview.
    
    Args:
        path (Path): Path to the file
        size (int): File size in bytes
        
    Returns:
        bool: True if the file should have a preview
    """
    # Maximum file size for preview (100KB)
    MAX_PREVIEW_SIZE = 100 * 1024
    
    # Check file size
    if size > MAX_PREVIEW_SIZE:
        return False
    
    # Only preview certain file extensions
    preview_exts = ['.md', '.txt', '.json', '.yaml', '.yml', '.py', '.js', '.html', '.css']
    return path.suffix.lower() in preview_exts


def get_file_preview(path, max_lines=20):
    """
    Get a preview of the file content.
    
    Args:
        path (Path): Path to the file
        max_lines (int): Maximum number of lines to include
        
    Returns:
        str: File preview or None on error
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append("...")
                    break
                lines.append(line.rstrip())
            return "\n".join(lines)
    except Exception:
        return None 