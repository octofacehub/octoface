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
octoface download "hf://username/cool-model"
```

### Upload models to IPFS and contribute to OctoFaceHub

```bash
# Upload local model with full details
octoface upload ./path/to/model --name "My Model" --description "A cool model" --tags "cool,awesome"

# Upload with minimal details (prompts for missing information)
octoface upload ./path/to/model

# Upload from HuggingFace in one step
octoface upload hf://username/cool-model
```

The upload command will:

1. Upload your model to IPFS
2. Check if you have push access to the repository
3. If you have push access, create a PR directly
4. If you don't have push access, automatically:
   - Create a fork of the repository (or use existing fork)
   - Create a branch
   - Add your model files
   - Create a pull request from your fork

No manual Git operations required!

### Generate files only (without submitting PR)

If you want to generate the model files without submitting a PR:

```bash
# Generate files using a local model directory
octoface generate-files --path "./path/to/model" --name "My Model" --description "A cool model" --tags "cool,awesome"

# Generate files using an existing IPFS CID
octoface generate-files --cid "bafybeih2qqh6rfmgrrggvkwsve7yuru72tm66vmp2cc5q7nmhytnovq7dm" --name "My Model" --description "A cool model" --tags "cool,awesome"

# Specify custom output directory
octoface generate-files --path "./path/to/model" --output "./my-files"
```

## Permissions

OctoFaceHub uses a directory-based permission model:

- Each GitHub user can only modify files in their own `models/username/` directory
- GitHub Actions validate that PRs only contain changes to your own directory
- The model-map.json is automatically updated when your PR is merged

## Contributing

Contributions to OctoFace CLI are welcome! Please feel free to submit a pull request.

## License

MIT
