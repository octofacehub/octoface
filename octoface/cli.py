"""Command-line interface for OctoFace."""

import os
import sys
import click
from rich.console import Console
import subprocess
import json

from octoface import __version__
from octoface.downloader import download_model
from octoface.uploader import upload_to_ipfs, generate_model_tree
from octoface.github import create_model_pr, test_github_access, get_github_username
from octoface.utils import check_credentials, generate_model_metadata, generate_readme

console = Console()

@click.group()
@click.version_option(version=__version__)
def cli():
    """
    OctoFace CLI - Tools for working with OctoFaceHub models.
    
    This CLI tool helps you upload models to IPFS and create pull requests 
    to add them to the OctoFaceHub. It also provides utilities for downloading
    models from IPFS and HuggingFace.
    
    Example commands:
    
    \b
    Upload a model:
    $ octoface upload --path ./my-model --name "My Model" --description "A cool model" --tags "cool,awesome"
    
    \b
    Generate files for manual submission:
    $ octoface generate-files --path ./my-model --name "My Model" --description "A description" --tags "tag1,tag2"
    
    \b
    Test GitHub API access:
    $ octoface test-github
    
    Environment variables:
    
    \b
    GITHUB_API_TOKEN: GitHub Personal Access Token (required for GitHub operations)
    """
    pass


@cli.command()
@click.argument("model_path")
@click.option("--output", "-o", default="./", help="Directory to save the model")
def download(model_path, output):
    """Download a model from HuggingFace."""
    try:
        result = download_model(model_path, output)
        if result:
            console.print(f"[green]Successfully downloaded model: {model_path}[/green]")
            console.print(f"Saved to: {result}")
        else:
            console.print("[red]Failed to download model[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True), required=False)
@click.option("--name", "-n", help="Name of the model.", type=str)
@click.option("--description", "-d", help="Description of the model.", type=str)
@click.option("--tags", "-t", help="Comma-separated list of tags.", type=str)
def upload(path, name, description, tags):
    """Upload a model to IPFS and create a pull request on GitHub.
    
    If the path is a HuggingFace model ID (starting with 'hf://'), the model will be
    downloaded from HuggingFace Hub first.
    
    Examples:
    
    \b
    # Upload local model with all options
    $ octoface upload ./path/to/model --name "My Model" --description "A description" --tags "tag1,tag2"
    
    \b
    # Upload from HuggingFace
    $ octoface upload hf://username/model-name --name "HF Model" --description "A model from HuggingFace"
    """
    # Check if GITHUB_API_TOKEN is set
    if not os.environ.get("GITHUB_API_TOKEN"):
        console.print("[red]GITHUB_API_TOKEN environment variable is not set.[/red]")
        console.print("[yellow]Please set it using: export GITHUB_API_TOKEN=\"your-github-api-token\"[/yellow]")
        sys.exit(1)
    
    # Process HuggingFace model ID
    if path and path.startswith("hf://"):
        console.print(f"Downloading model from HuggingFace: {path[5:]}")
        model_path = download_model(path[5:])
        if not model_path:
            console.print("[red]Failed to download model.[/red]")
            sys.exit(1)
        path = model_path
    
    # Get model name if not provided
    if not name and path:
        # Use the directory name as the model name
        name = os.path.basename(os.path.abspath(path))
        console.print(f"Using directory name as model name: {name}")
    
    if not name:
        console.print("[red]Model name is required.[/red]")
        sys.exit(1)
    
    # Get description if not provided
    if not description:
        description = click.prompt("Enter a description for the model", default="")
    
    # Get tags if not provided
    if not tags:
        tags = click.prompt("Enter comma-separated tags for the model", default="")
    
    # Convert tags string to list
    tags_list = [tag.strip() for tag in tags.split(",")]
    
    # Upload model to IPFS
    console.print(f"Uploading model to IPFS: {path}")
    cid = upload_to_ipfs(path)
    if not cid:
        console.print("[red]Failed to upload model to IPFS.[/red]")
        sys.exit(1)
    
    console.print(f"[green]Model uploaded to IPFS with CID: {cid}[/green]")
    console.print(f"[green]View your model at https://w3s.link/ipfs/{cid}[/green]")
    
    # Create pull request on GitHub
    console.print("")
    console.print("[bold]Creating GitHub Pull Request...[/bold]")
    console.print("[yellow]This process will:[/yellow]")
    console.print("[yellow]1. Check if you have direct push access to the repository[/yellow]")
    console.print("[yellow]2. If you do, create a PR directly[/yellow]")
    console.print("[yellow]3. If not, automatically create a fork, add files, and submit a PR from your fork[/yellow]")
    console.print("")
    
    # Test GitHub access before proceeding
    console.print("Testing GitHub API access...")
    if not test_github_access():
        console.print("[red]Failed to access GitHub API. Please check your token and internet connection.[/red]")
        sys.exit(1)
    
    pr_url = create_model_pr(name, description, tags, cid, path)
    
    if pr_url:
        console.print("")
        console.print(f"[bold green]Model submission complete![/bold green]")
        console.print(f"[green]IPFS CID: {cid}[/green]")
        console.print(f"[green]Pull Request: {pr_url}[/green]")
        console.print("")
        console.print("[yellow]The OctoFaceHub team will review your submission.[/yellow]")
    else:
        console.print("")
        console.print("[yellow]Model was uploaded to IPFS but the GitHub PR process failed.[/yellow]")
        console.print(f"[green]IPFS CID: {cid}[/green]")
        console.print(f"[green]Access at: https://w3s.link/ipfs/{cid}[/green]")
        console.print("")
        console.print("[yellow]You can try again later or use 'octoface generate-files' to manually create the files.[/yellow]")
        sys.exit(1)


@cli.command()
def test_github():
    """Test GitHub API access."""
    if test_github_access():
        console.print("[green]GitHub API access successful![/green]")
    else:
        console.print("[red]GitHub API access failed.[/red]")
        sys.exit(1)


@cli.command()
@click.option("--email", help="Email address for w3 login")
def setup_w3(email):
    """
    Set up web3.storage credentials.
    
    This will guide you through the process of setting up your web3.storage credentials.
    """
    # Check if w3cli is installed
    try:
        result = subprocess.run(["w3", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            console.print("[red]w3cli not found. Installing w3cli...[/red]")
            console.print("[yellow]This may take a moment...[/yellow]")
            npm_result = subprocess.run(["npm", "i", "--global", "@web3-storage/w3cli"], capture_output=True, text=True)
            if npm_result.returncode != 0:
                console.print("[red]Failed to install w3cli. Please install it manually:[/red]")
                console.print("[yellow]npm i --global @web3-storage/w3cli[/yellow]")
                sys.exit(1)
            else:
                console.print("[green]Successfully installed w3cli.[/green]")
    except FileNotFoundError:
        console.print("[red]w3cli not found. Installing w3cli...[/red]")
        console.print("[yellow]This may take a moment...[/yellow]")
        npm_result = subprocess.run(["npm", "i", "--global", "@web3-storage/w3cli"], capture_output=True, text=True)
        if npm_result.returncode != 0:
            console.print("[red]Failed to install w3cli. Please install it manually:[/red]")
            console.print("[yellow]npm i --global @web3-storage/w3cli[/yellow]")
            sys.exit(1)
        else:
            console.print("[green]Successfully installed w3cli.[/green]")
    
    # Check if already logged in
    try:
        did_result = subprocess.run(["w3", "did"], capture_output=True, text=True)
        if did_result.returncode == 0 and "did:key:" in did_result.stdout:
            console.print("[green]Already logged in to web3.storage.[/green]")
            
            # Check if space exists
            space_result = subprocess.run(["w3", "space", "ls"], capture_output=True, text=True)
            if space_result.returncode == 0 and space_result.stdout.strip():
                console.print("[green]Space already exists.[/green]")
                return
            else:
                console.print("[yellow]No space found. Creating a new space...[/yellow]")
                # Continue to create space
        else:
            # Need to log in
            if not email:
                console.print("[yellow]Please provide an email address for w3 login.[/yellow]")
                console.print("[yellow]Example: octoface setup-w3 --email your.email@example.com[/yellow]")
                sys.exit(1)
            
            console.print(f"[yellow]Logging in with email: {email}[/yellow]")
            console.print("[yellow]This will send a verification link to your email.[/yellow]")
            console.print("[yellow]Please check your email and click the verification link.[/yellow]")
            
            login_result = subprocess.run(["w3", "login", "--email", email], capture_output=True, text=True)
            if login_result.returncode != 0:
                console.print("[red]Failed to log in. Please try again later or use a different email.[/red]")
                console.print(f"[red]Error: {login_result.stderr}[/red]")
                sys.exit(1)
            
            console.print("[green]Login process initiated. Check your email for a verification link.[/green]")
            console.print("[yellow]After clicking the verification link, run this command again to create a space.[/yellow]")
            sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error checking w3 login status: {str(e)}[/red]")
        if not email:
            console.print("[yellow]Please provide an email address for w3 login.[/yellow]")
            console.print("[yellow]Example: octoface setup-w3 --email your.email@example.com[/yellow]")
            sys.exit(1)
        
        console.print(f"[yellow]Attempting to log in with email: {email}[/yellow]")
        console.print("[yellow]This will send a verification link to your email.[/yellow]")
        
        try:
            login_result = subprocess.run(["w3", "login", "--email", email], capture_output=True, text=True)
            if login_result.returncode != 0:
                console.print("[red]Failed to log in. Please try again later or use a different email.[/red]")
                console.print(f"[red]Error: {login_result.stderr}[/red]")
                sys.exit(1)
            
            console.print("[green]Login process initiated. Check your email for a verification link.[/green]")
            console.print("[yellow]After clicking the verification link, run this command again to create a space.[/yellow]")
            sys.exit(0)
        except Exception as login_err:
            console.print(f"[red]Error initiating login: {str(login_err)}[/red]")
            sys.exit(1)
    
    # Create space if needed
    try:
        space_result = subprocess.run(["w3", "space", "create", "octoface-space"], capture_output=True, text=True)
        if space_result.returncode != 0:
            console.print("[red]Failed to create space. Please try again later.[/red]")
            console.print(f"[red]Error: {space_result.stderr}[/red]")
            sys.exit(1)
        
        console.print("[green]Successfully created space.[/green]")
        
        # Use the space
        use_result = subprocess.run(["w3", "space", "use", "octoface-space"], capture_output=True, text=True)
        if use_result.returncode != 0:
            console.print("[red]Failed to use space. Please try again later.[/red]")
            console.print(f"[red]Error: {use_result.stderr}[/red]")
            sys.exit(1)
        
        console.print("[green]Successfully set up web3.storage credentials.[/green]")
        console.print("[green]You are now ready to upload models to IPFS.[/green]")
    except Exception as e:
        console.print(f"[red]Error setting up space: {str(e)}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    "--path",
    "-p",
    help="Path to the model directory.",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option("--name", "-n", help="Name of the model.", required=True, type=str)
@click.option("--description", "-d", help="Description of the model.", required=True, type=str)
@click.option(
    "--tags", "-t", help="Comma-separated list of tags.", required=True, type=str
)
@click.option(
    "--cid",
    "-c",
    help="CID of the model on IPFS. If not provided, the model will be uploaded.",
    type=str,
)
@click.option(
    "--output",
    "-o",
    help="Output directory for generated files.",
    type=click.Path(file_okay=False, dir_okay=True),
    default="octofacehub_files",
)
def generate_files(path, name, description, tags, cid, output):
    """Generate files for manual submission to OctoFaceHub.
    
    This command generates the necessary files for submitting a model to OctoFaceHub
    without creating a PR. You can then manually add these files to your fork of the
    OctoFaceHub repository.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output, exist_ok=True)
    
    # Check if GitHub token is set
    github_token = os.environ.get("GITHUB_API_TOKEN")
    if not github_token:
        console.print("[yellow]Warning: GITHUB_API_TOKEN environment variable not set.[/yellow]")
        console.print("[yellow]Some GitHub-related information may not be available.[/yellow]")
    
    # Process HuggingFace model ID
    if path and path.startswith("hf://"):
        console.print(f"Downloading model from HuggingFace: {path[5:]}")
        model_path = download_model(path[5:])
        if not model_path:
            console.print("[red]Failed to download model.[/red]")
            sys.exit(1)
        path = model_path
    
    # Upload to IPFS if CID not provided
    if not cid and path:
        console.print(f"Uploading model to IPFS: {path}")
        cid = upload_to_ipfs(path)
        if not cid:
            console.print("[red]Failed to upload model to IPFS.[/red]")
            sys.exit(1)
        console.print(f"[green]Model uploaded to IPFS with CID: {cid}[/green]")
        console.print(f"[green]View your model at https://w3s.link/ipfs/{cid}[/green]")
    elif not cid and not path:
        console.print("[red]Either --path or --cid must be provided.[/red]")
        sys.exit(1)
    
    # Generate model metadata
    tags_list = [tag.strip() for tag in tags.split(",")]
    metadata = generate_model_metadata(name, description, tags_list, cid)
    
    # Generate README
    readme = generate_readme(name, description, tags_list, cid)
    
    # Generate model tree
    model_tree = generate_model_tree(name, metadata, readme)
    
    # Get GitHub username if token is available
    github_username = get_github_username() 
    if not github_username:
        github_username = "anonymous"
        console.print("[yellow]GitHub username not available, using 'anonymous'[/yellow]")
    
    # Write files to output directory
    model_name = name.lower().replace(" ", "-")
    user_dir = os.path.join(output, github_username)
    os.makedirs(user_dir, exist_ok=True)
    model_dir = os.path.join(user_dir, model_name)
    os.makedirs(model_dir, exist_ok=True)
    
    with open(os.path.join(model_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    
    with open(os.path.join(model_dir, "README.md"), "w") as f:
        f.write(readme)
    
    # Write guide for adding model to OctoFaceHub
    guide = f"""# How to Add Your Model to OctoFaceHub

Your model has been successfully uploaded to IPFS with CID: {cid}
View your model at: https://w3s.link/ipfs/{cid}

To add your model to OctoFaceHub, follow these steps:

1. Fork the OctoFaceHub repository: https://github.com/octofacehub/octofacehub.github.io
2. Clone your fork:
   ```
   git clone https://github.com/{github_username}/octofacehub.github.io.git
   cd octofacehub.github.io
   ```
3. Copy the generated files to your cloned repository:
   ```
   mkdir -p models/{github_username}/{model_name}
   cp -r {model_dir}/* models/{github_username}/{model_name}/
   ```
4. Commit and push your changes:
   ```
   git add models/{github_username}/{model_name}
   git commit -m "Add {name} model"
   git push
   ```
5. Create a pull request from your fork to the main repository.

The generated files are located at: {model_dir}
"""
    
    with open(os.path.join(output, "GUIDE.md"), "w") as f:
        f.write(guide)
    
    console.print(f"[green]Files generated successfully at: {output}[/green]")
    console.print(f"[green]Follow the instructions in {os.path.join(output, 'GUIDE.md')} to add your model to OctoFaceHub.[/green]")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main() 