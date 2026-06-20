# Claude Code with Amazon Bedrock and IAM Identity Center Authentication

## Project Overview

This project provides a Python implementation for integrating Claude Code with Amazon Bedrock, leveraging AWS IAM Identity Center (formerly AWS SSO) for authentication. It enables secure, identity-based access to Claude models through Bedrock without managing long-lived credentials.

## Development Setup

### Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- AWS Account with Bedrock access
- IAM Identity Center configured

### Getting Started

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Create and activate virtual environment**:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   uv pip install -e .
   # Or for development with extras:
   uv pip install -e ".[dev]"
   ```

4. **Configure AWS credentials** via IAM Identity Center:
   ```bash
   aws configure sso
   # Follow prompts to set up your IAM Identity Center profile
   aws sso login --profile your-profile-name
   ```

## Project Structure

```
├── CLAUDE.md                 # This file
├── pyproject.toml           # Project configuration and dependencies
├── src/
│   └── claude_bedrock_idc/   # Main package
│       ├── __init__.py
│       ├── auth/             # IAM Identity Center authentication
│       ├── client/           # Bedrock client integration
│       └── models/           # Data models and types
├── tests/                    # Test suite
└── docs/                     # Documentation
```

## Key Features

- **IAM Identity Center Authentication**: Secure, keyless authentication using AWS SSO
- **Bedrock Integration**: Direct access to Claude models via Amazon Bedrock
- **Token Management**: Automatic credential refresh and session handling
- **Error Handling**: Robust error handling for auth failures and API errors

## Development Workflow

### Using uv for Package Management

- **Add a dependency**: `uv pip install package-name`
- **Add a dev dependency**: Edit `pyproject.toml` and add to `[project.optional-dependencies]` under `dev`
- **Update dependencies**: `uv pip install -e ".[dev]" --upgrade`
- **List installed packages**: `uv pip list`

### Running Tests

```bash
# Install test dependencies
uv pip install -e ".[test]"

# Run all tests
pytest

# Run with coverage
pytest --cov=src/claude_bedrock_idc
```

### Authentication Notes

- The project uses AWS SDK (boto3) under the hood
- IAM Identity Center credentials are automatically discovered from `~/.aws/config` and `~/.aws/credentials`
- Token refresh is handled automatically; no manual credential rotation needed
- For local development, ensure you've run `aws sso login --profile your-profile`

## Configuration

### Environment Variables

- `AWS_PROFILE`: Specify which IAM Identity Center profile to use (optional, uses default if not set)
- `AWS_REGION`: AWS region for Bedrock access (default: us-east-1)
- `BEDROCK_MODEL_ID`: Claude model ID to use (e.g., `anthropic.claude-3-sonnet-20240229-v1:0`)

### AWS Credentials

IAM Identity Center tokens are cached in:
- Linux/macOS: `~/.aws/sso/cache/`
- Windows: `%USERPROFILE%\.aws\sso\cache\`

## Common Tasks

### Testing Authentication
```bash
python -c "from claude_bedrock_idc import get_authenticated_client; client = get_authenticated_client(); print('Auth successful')"
```

### Running the Application
```bash
python -m claude_bedrock_idc.main
```

## Dependencies

Key dependencies managed via uv:
- **boto3**: AWS SDK for Python
- **anthropic**: Anthropic SDK for Claude models
- **pydantic**: Data validation and settings management
- **pytest**: Testing framework (dev)

## Troubleshooting

### Authentication Issues
- Run `aws sso login --profile your-profile` to refresh tokens
- Check `aws sts get-caller-identity --profile your-profile` to verify credentials
- Review IAM Identity Center permissions in AWS console

### Bedrock Access Issues
- Verify your IAM user/role has `bedrock:InvokeModel` permissions
- Confirm Bedrock is available in your AWS region
- Check model ID matches your regional availability

### Virtual Environment Issues
- Delete `.venv/` and run `uv venv` again if encountering issues
- Ensure Python 3.8+ is available: `python --version`

## Notes for Claude Code

- This project uses `uv` exclusively for dependency management (not pip directly)
- When adding new dependencies, update `pyproject.toml` and run `uv pip install -e .`
- IAM Identity Center provides seamless, secure authentication without credential management overhead
- All authentication logic should centralize in the `auth/` module to maintain security best practices
