# theundercut

## Environment Setup

For local development:

1. Copy `.env.example` to `.env` and update the values as needed:
   ```
   cp .env.example .env
   ```

2. Use the `.env` file for your development environment. The docker-compose.dev.yml file will automatically use these variables.

**Important**: Never commit your `.env` file to version control as it contains sensitive information.