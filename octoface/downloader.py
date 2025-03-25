"""Module for downloading models from HuggingFace."""

import os
import sys
from pathlib import Path
from rich.console import Console
from rich.progress import Progress

console = Console()

def download_model(model_id, output_dir="./"):
    """
    Download a model from HuggingFace.
    
    Args:
        model_id (str): HuggingFace model ID (username/model)
        output_dir (str): Directory to save the model
        
    Returns:
        str: Path to the downloaded model or None on failure
    """
    try:
        # Import huggingface_hub
        from huggingface_hub import snapshot_download
        
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Extract model name from ID
        model_name = model_id.split("/")[-1]
        
        # Set model directory
        model_dir = output_path / model_name
        
        # Download model
        with Progress() as progress:
            task = progress.add_task(f"[cyan]Downloading {model_id}...", total=None)
            
            try:
                # Use huggingface_hub to download the model
                snapshot_download(
                    repo_id=model_id,
                    local_dir=str(model_dir),
                    local_dir_use_symlinks=False,
                )
                progress.update(task, completed=100)
            except Exception as e:
                console.print(f"[red]Error downloading model: {str(e)}[/red]")
                return None
        
        console.print(f"[green]Model downloaded successfully to: {model_dir}[/green]")
        return str(model_dir)
    
    except ImportError:
        console.print("[red]huggingface_hub package is not installed. Installing...[/red]")
        
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])
            console.print("[green]huggingface_hub installed successfully. Retrying download...[/green]")
            return download_model(model_id, output_dir)
        except Exception as e:
            console.print(f"[red]Failed to install huggingface_hub: {str(e)}[/red]")
            return None
    
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return None 