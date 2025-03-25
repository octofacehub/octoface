# Changelog

All notable changes to the OctoFace CLI will be documented in this file.

## [0.4.0] - 2023-07-31

### Added

- Fully automated fork-and-PR workflow for third-party contributors
- GitHub API integration for creating forks, branches, and PRs
- No more manual Git operations needed for model submission
- Better error handling and user guidance during the submission process

### Changed

- Improved CLI output with clearer instructions
- Streamlined upload command with better prompts for missing data
- Updated documentation to reflect the simplified workflow

## [0.3.0] - 2023-07-31

### Added

- Enhanced GitHub Actions workflow for validating PR changes
- Automated model-map.json updates when users add or modify models
- Improved error handling for unauthorized access
- Better instructions for third-party contributors

### Changed

- Improved user permission model based on GitHub usernames
- Updated documentation to reflect new contribution process
- Enhanced error messages for better user experience

### Fixed

- Fixed handling of GitHub token validation
- Fixed error handling for anonymous users
- Fixed path handling in model directory generation

## [0.2.0] - 2023-07-20

### Added

- `generate-files` command for users without push access
- Support for manual model submission
- Improved error handling and user feedback

### Changed

- Enhanced permission checking logic
- Updated documentation and examples

## [0.1.0] - 2023-07-10

### Added

- Initial release
- IPFS upload functionality
- GitHub PR creation
- Basic model metadata handling
