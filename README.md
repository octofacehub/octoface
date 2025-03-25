# OctoFace CLI

A command-line tool for managing LLM models on IPFS and GitHub Pages.

## Installation

```bash
pip install octoface
```

## Usage

### Set up credentials

```bash
# Set GitHub API token
export GITHUB_API_TOKEN="your-github-api-token"

# Set up web3.storage
npm i --global @web3-storage/w3cli
w3 login  # Follow prompts to authenticate
w3 space create my-space-name  # Create a storage space
w3 space use my-space-name     # Select the space for uploads
```

### Test GitHub API access

```bash
octoface test-github
```

### Download models from HuggingFace

```bash
octoface download "hf-username/cool-model"
```

### Upload models to IPFS and GitHub

```bash
# Upload local model
octoface upload . --name "gemma-3-4b-it"

# Upload with description
octoface upload "./path/to/model/gemma-3-4b-it" --description "State-of-the-art open models from Google"

# Upload with tags
octoface upload "./path/to/model" --name "My Model" --description "A cool model" --tags "cool,awesome"

# Download from HF and upload in one step
octoface upload "hf-username/cool-model"
```

### Generate files for manual submission

If you don't have push access to the OctoFaceHub repository, you can generate the necessary files and submit them manually:

```bash
# Generate files using a local model directory
octoface generate-files --path "./path/to/model" --name "My Model" --description "A cool model" --tags "cool,awesome"

# Generate files using an existing IPFS CID
octoface generate-files --cid "bafybeih2qqh6rfmgrrggvkwsve7yuru72tm66vmp2cc5q7nmhytnovq7dm" --name "My Model" --description "A cool model" --tags "cool,awesome"

# Specify custom output directory
octoface generate-files --path "./path/to/model" --name "My Model" --description "A cool model" --tags "cool,awesome" --output "./my-files"
```

After generating the files, follow the instructions in the GUIDE.md file to submit your model to OctoFaceHub.

## License

MIT
