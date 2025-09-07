# Agent Instructions

## 🚨 CRITICAL: MANDATORY READING
**ALL SESSIONS MUST READ AND FOLLOW THIS DOCUMENT COMPLETELY**
- This document contains CRITICAL security and implementation guidelines
- Every agent session MUST review this file before any actions
- NO EXCEPTIONS: Failure to follow these guidelines is prohibited

## Overview
This document contains instructions and guidelines for AI agents working with the SerpAPI project.

## Project Context
- **Project Name**: SerpAPI
- **Workspace Location**: `C:\Users\MY PC\SerpAPI`
- **Date Created**: September 6, 2025

## System Requirements
This system will:
- Use an API to retrieve data online
- Save ALL raw data from EVERY API query execution to a local database file
- **ENHANCED**: Search local database FIRST before making API calls (smart caching)
- **DATA FRESHNESS**: All flight data has a 24-hour maximum lifespan and is automatically cleaned up
- **CACHE POLICY**: Database is checked first only to avoid redundant API calls within 24 hours
- **PRODUCTION**: Real SerpAPI key configured and ready for live data collection
- Implement a database schema designed by the agent (requires user confirmation)
- Maintain complete data persistence for all API interactions
- Store ALL temporary scripts in `/Temp` directory
- Store ALL temporary data in `/Temp` directory
- **CRITICAL**: Clean ALL temp scripts after every successful operation
 - **UPDATED (2025-09-08)**: All temporary, experimental, or ad-hoc test scripts MUST be placed under the `/tests` directory (no `/Temp` directory is to be used)
 - Temporary scripts in `/tests` must be clearly named with a `temp_` or `experimental_` prefix and either converted to proper tests or removed before finalization
- Store ALL database files and related scripts in `/DB` directory
- Store ALL main files and scripts in `/Main` directory
- **PROHIBITED**: Mock data is NOT allowed at any time - use real API data only

## Agent Responsibilities

### 🚨 MANDATORY: READ AGENT INSTRUCTIONS FIRST
### 🚨 CRITICAL: All implementation needs confirmation
### 🚨 CRITICAL: All actions by the agent will have to be confirmed
### 🚨 CRITICAL: ALL security guidelines must be strictly followed

### Primary Tasks
1. **Security First**
   - Review and follow ALL security guidelines before any implementation
   - Ensure no sensitive data exposure in any form
   - Use secure coding practices throughout

2. **Code Development**
   - Write clean, maintainable code
   - Follow established coding standards
   - Implement proper error handling
   - **CRITICAL**: Never include sensitive data in code or logs

3. **API Integration**
   - Handle SerpAPI integration efficiently
   - Manage API keys securely through environment variables ONLY
   - Implement rate limiting and retry logic
   - **CRITICAL**: Save ALL raw data from EVERY API query to local database
   - Ensure no data loss during API interactions
   - **CRITICAL**: Never log or expose API keys

3. **Database Management**
   - Design appropriate database schema (requires user confirmation)
   - **CRITICAL**: Do NOT create new databases unless explicitly confirmed by user TWICE
   - **CRITICAL**: Use existing Main_DB.db - do not create additional database files
   - **DATABASE POLICY**: Always use Main_DB.db for all data storage operations
   - Implement data persistence for all API responses
   - **AIRPORT & AIRLINE DATA**: Store complete airport and airline information from flight segments
   - **24-HOUR FRESHNESS**: Automatically clean up flight data older than 24 hours
   - **COMPREHENSIVE STORAGE**: Store flight searches, results, segments, layovers, and price insights
   - Maintain data integrity and consistency
   - Provide efficient data retrieval mechanisms
   - Store all database files in `/DB` directory
   - Store all database-related scripts in `/DB` directory

3. **Documentation**
   - Maintain up-to-date documentation
   - Write clear comments in code
   - Update README files as needed
   - Document database schema and API data flow

### Code Standards
- Use descriptive variable and function names
- Follow language-specific conventions
- Implement proper logging
- Write unit tests for critical functions
 - **TEMP/TEST POLICY**: All temporary or experimental scripts go in `/tests` only (no `/Temp` folder). Prefix with `temp_` and remove or promote to real tests before merge
 - **CRITICAL**: Remove obsolete temp scripts once purpose is fulfilled
- Store all database files and related scripts in `/DB` directory
- Store all main files and scripts in `/Main` directory
- **NEVER use mock data** - always use real API data
- **CRITICAL COMMUNICATION RULE**: Do NOT create unnecessary summaries or reports unless explicitly requested by the user
- **RESPONSE POLICY**: Keep responses concise and focused on the specific task requested
- **NO AUTO-SUMMARIES**: Avoid generating summaries, reports, or comprehensive overviews unless the user specifically asks for them
 - **DEPENDENCIES (CRITICAL)**: Only introduce packages that are actively maintained, widely adopted, and security-reviewed; prefer Python standard library when possible; REQUIRE user approval (double-confirm) before adding any new external dependency; pin versions in `requirements.txt` and avoid unpinned `latest` installs; remove unused or deprecated packages promptly

### Security Guidelines
- Never expose API keys in code or configuration files
- Use environment variables for sensitive data only
- **CRITICAL**: API keys must NEVER be stored in plain text files
- **CRITICAL**: API keys must NEVER be logged or printed to console
- **CRITICAL**: API keys must NEVER appear in error messages
- **CRITICAL**: API keys must NEVER be committed to version control
- **CRITICAL**: API keys must NEVER be transmitted over insecure connections
- Validate all user inputs to prevent injection attacks
- Implement proper authentication and authorization
- Use HTTPS for all API communications
- Sanitize all outputs to prevent data leakage
- Follow principle of least privilege for file access
- Implement proper error handling without exposing sensitive information
- **MANDATORY**: All implementations must follow these security guidelines

### Error Handling
- Provide meaningful error messages
- Log errors appropriately
- Implement graceful fallbacks
- Handle network timeouts and failures

## Development Workflow
1. **🚨 MANDATORY: Read this agent-instructions.md file completely**
2. Analyze requirements thoroughly
3. **Design database schema and get user confirmation**
4. **Request confirmation for all planned actions**
5. Plan implementation approach with security considerations
6. **Get approval before writing any code**
7. Write code with proper structure and security measures
8. **Ensure all API data is saved to local database**
9. **Verify no sensitive data exposure in any output**
10. Test functionality thoroughly
11. Document changes securely
12. Review and refactor if needed
13. **Confirm all changes with user before finalizing**

## Best Practices
- **🚨 FIRST: Always read agent-instructions.md completely**
- Keep functions small and focused
- Use meaningful commit messages
- Regularly backup important work
- Follow DRY (Don't Repeat Yourself) principle
- Implement proper code organization
 - Place any temporary / exploratory scripts ONLY in `/tests` (prefixed `temp_`) and clean them promptly
- Use `/DB` directory for all database files and related scripts
- Use `/Main` directory for all main files and scripts
- Always work with real API data, never mock data
- **SECURITY**: Never expose sensitive information in any form
- **SECURITY**: Validate all inputs and sanitize all outputs
- **SECURITY**: Use secure coding practices throughout

## Communication
- **🚨 MANDATORY**: Read and acknowledge these agent instructions before proceeding
- Provide clear explanations of changes
- Ask for clarification when requirements are unclear
- Document assumptions made during development
- Report any blockers or issues promptly
- **MANDATORY**: Request confirmation before executing any action
- **MANDATORY**: Wait for user approval before proceeding with implementation
- **SECURITY**: Never include sensitive data in communications
- **SECURITY**: Sanitize all outputs to prevent data exposure

## Notes
- This file should be updated as the project evolves
- All team members should review these instructions
- Suggestions for improvements are welcome
- **🚨 CRITICAL**: This file MUST be read by every agent session

## 🔒 COMPREHENSIVE SECURITY REQUIREMENTS

### API Key Security (CRITICAL)
- ❌ **NEVER** store API keys in plain text files
- ❌ **NEVER** include API keys in source code
- ❌ **NEVER** log API keys to console or files
- ❌ **NEVER** include API keys in error messages
- ❌ **NEVER** commit API keys to version control
- ❌ **NEVER** transmit API keys over insecure connections
- ✅ **ONLY** use environment variables for API key storage
- ✅ **ALWAYS** validate environment variable availability
- ✅ **ALWAYS** use secure error handling for missing keys

### Data Security (CRITICAL)
- ✅ **ALWAYS** validate all user inputs
- ✅ **ALWAYS** sanitize all outputs
- ✅ **ALWAYS** use parameterized database queries
- ✅ **ALWAYS** implement proper error handling
- ❌ **NEVER** expose internal system details in errors
- ❌ **NEVER** include sensitive data in debug output
- ❌ **NEVER** store unencrypted sensitive data

### Code Security (CRITICAL)
- ✅ **ALWAYS** follow principle of least privilege
- ✅ **ALWAYS** validate file paths and operations
- ✅ **ALWAYS** use secure coding practices
- ✅ **ALWAYS** implement proper authentication
- ❌ **NEVER** execute untrusted code
- ❌ **NEVER** bypass security controls
- ❌ **NEVER** ignore security warnings

### Communication Security (CRITICAL)
- ✅ **ALWAYS** use HTTPS for API communications
- ✅ **ALWAYS** validate SSL/TLS certificates
- ✅ **ALWAYS** implement proper timeouts
- ❌ **NEVER** transmit sensitive data over HTTP
- ❌ **NEVER** ignore certificate errors
- ❌ **NEVER** use deprecated security protocols

### 🚨 VIOLATION CONSEQUENCES
- **Any violation of these security guidelines is prohibited**
- **All implementations must be reviewed for security compliance**
- **Security violations require immediate correction**
- **No exceptions to security requirements are permitted**

---
*Last Updated: September 6, 2025*
*Dependency Policy Updated: September 8, 2025*
*Security Guidelines: MANDATORY COMPLIANCE REQUIRED*
