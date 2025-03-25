# Changelog

All notable changes to the Octoface CLI will be documented in this file.

## [0.2.0] - 2023-03-25

### Added

- New directory structure using `models/github-username/model-name/`
- Improved validation for ensuring author matches directory name
- Added `generate-files` command for users without push access
- PyPI publishing workflow with OIDC authentication
- Basic test suite with pytest

### Changed

- Updated GitHub integration to check for push access
- Modified the model map update logic to use path-based lookup
- Improved error handling and user feedback

## [0.1.0] - 2023-03-24

### Added

- Initial release of the Octoface CLI tool
- Support for uploading models to IPFS
- Integration with GitHub for creating pull requests
- Basic model metadata generation
- HuggingFace model download support
