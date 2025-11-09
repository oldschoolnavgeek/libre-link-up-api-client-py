# Documentation Context Index

This document provides a quick reference to all documentation files in this project. Use this index to navigate and understand the documentation structure.

## Documentation Files

### SETUP.md
**Purpose**: Complete Google Cloud Platform setup guide  
**Content**:
- Step-by-step instructions for enabling required APIs
- Cloud SQL PostgreSQL instance creation
- Secret Manager setup and IAM permissions
- VPC connector configuration
- IAM roles and permissions
- Deployment verification
- Cost estimation
**When to use**: First-time setup, setting up a new environment, troubleshooting deployment issues

### QUICK_START.md
**Purpose**: Get started quickly with local testing and basic deployment  
**Content**: 
- 5-minute local setup guide
- Docker Compose commands
- Basic API testing examples
- Common troubleshooting tips
**When to use**: First-time setup, quick reference for common commands

### DEPLOYMENT.md
**Purpose**: Complete step-by-step guide for deploying to Google Cloud Run  
**Content**:
- Cloud SQL PostgreSQL setup
- Secret Manager configuration
- VPC Connector setup
- Cloud Run service and job deployment
- Cloud Scheduler configuration
- Troubleshooting guide
**When to use**: Production deployment, infrastructure setup, troubleshooting deployment issues

### GOOGLE_SHEETS_INTEGRATION.md
**Purpose**: Guide for integrating with Google Sheets and Looker Studio  
**Content**:
- Google Apps Script examples
- Multiple integration methods (IMPORTDATA, Apps Script, Web Connector)
- Looker Studio connector setup
- Scheduled data import patterns
- Security considerations
**When to use**: Setting up external data access, creating dashboards, integrating with Google Workspace

### README_DATABASE_SERVICE.md
**Purpose**: Overview and reference for the database service  
**Content**:
- Service architecture and features
- API endpoint documentation
- Database schema
- Configuration options
- Development guide
- Monitoring and troubleshooting
**When to use**: Understanding the service architecture, API reference, development work

### IMPLEMENTATION_SUMMARY.md
**Purpose**: Summary of completed implementation  
**Content**:
- List of all implemented components
- Architecture diagram
- Next steps checklist
- Testing checklist
- Cost estimation
- Documentation index
**When to use**: Understanding what's been implemented, project status overview, planning next steps

### CONNECTION_IDENTIFIER_EXPLANATION.md
**Purpose**: Explains how to use connection identifiers for multiple patients  
**Content**:
- How to specify which patient/connection to use
- Examples of connection identifier usage
- Multiple patient scenarios
**When to use**: Working with multiple LibreLinkUp connections, understanding patient selection

### CONFIGURATION.md
**Purpose**: Guide for managing configuration files and environment variables  
**Content**:
- .env file setup for deployment constants
- config.yaml for local development
- Environment variables and Secret Manager
- Configuration priority and best practices
- Deployment script usage
**When to use**: Setting up configuration, understanding how config is loaded, troubleshooting config issues

## Documentation Structure

```
docs/
├── context_index.md (this file)
├── SETUP.md (Google Cloud setup - start here for cloud deployment)
├── QUICK_START.md (local development quick start)
├── CONFIGURATION.md (config management)
├── DEPLOYMENT.md (production deployment)
├── GOOGLE_SHEETS_INTEGRATION.md (external integrations)
├── README_DATABASE_SERVICE.md (service reference)
├── IMPLEMENTATION_SUMMARY.md (project status)
├── CONNECTION_IDENTIFIER_EXPLANATION.md (multi-patient setup)
└── TROUBLESHOOTING.md (common issues and solutions)
```

## Quick Navigation Guide

**New to the project?**
1. Start with `QUICK_START.md` for local setup
2. Read `README_DATABASE_SERVICE.md` for service overview
3. Check `IMPLEMENTATION_SUMMARY.md` for project status

**Deploying to production?**
1. Start with `SETUP.md` for Google Cloud infrastructure setup
2. Follow `DEPLOYMENT.md` for detailed deployment steps
3. Reference `QUICK_START.md` for common commands
4. Use `GOOGLE_SHEETS_INTEGRATION.md` for external access setup

**Integrating with external tools?**
1. See `GOOGLE_SHEETS_INTEGRATION.md` for Google Workspace integration
2. Reference `README_DATABASE_SERVICE.md` for API endpoints
3. Check `DEPLOYMENT.md` for API URL and authentication

**Troubleshooting?**
- `QUICK_START.md` - Common local issues
- `DEPLOYMENT.md` - Deployment and infrastructure issues
- `README_DATABASE_SERVICE.md` - Service-specific troubleshooting

## Key Concepts

**Service Architecture**: See `README_DATABASE_SERVICE.md` for architecture diagram and component overview

**API Endpoints**: Documented in `README_DATABASE_SERVICE.md` with examples in `QUICK_START.md`

**Database Schema**: Defined in `README_DATABASE_SERVICE.md`

**Configuration**: 
- Local: `config.yaml.example` (in root)
- Cloud: Environment variables (see `DEPLOYMENT.md`)

**Integration Patterns**: Multiple methods documented in `GOOGLE_SHEETS_INTEGRATION.md`

## Notes for AI Context

- All documentation files are in the `docs/` folder
- References between docs use relative paths (e.g., `./DEPLOYMENT.md`)
- References from root README should use `docs/FILENAME.md`
- The main README.md in root is for the original LibreLinkUp client, not the database service
- Service-specific documentation is in `docs/README_DATABASE_SERVICE.md`

