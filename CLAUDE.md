# CLAUDE.md - AI Assistant Guide

This document provides guidance for AI assistants working with the `codings` repository.

## Project Overview

**Repository:** codings
**Status:** New/Initial Setup
**Description:** This is a newly initialized repository ready for development.

## Current State

This repository is in its initial state with minimal setup:

- Single README.md file
- Git repository initialized
- No source code, dependencies, or configuration files yet

## Directory Structure

```
codings/
├── .git/           # Git repository metadata
├── CLAUDE.md       # This file - AI assistant guide
└── README.md       # Project readme
```

## Development Guidelines

### When Adding New Features

1. **Choose appropriate technology** based on project requirements
2. **Create standard directory structure**:
   - `src/` - Source code
   - `tests/` or `__tests__/` - Test files
   - `docs/` - Documentation
   - `config/` - Configuration files

3. **Initialize package management** if using Node.js:
   ```bash
   npm init -y
   ```

4. **Set up essential tooling**:
   - Linter (ESLint, Pylint, etc.)
   - Formatter (Prettier, Black, etc.)
   - Test framework (Jest, pytest, etc.)

### Code Conventions to Follow

#### General Practices

- Write clear, self-documenting code
- Include meaningful comments for complex logic
- Follow consistent naming conventions
- Keep functions small and focused
- Handle errors appropriately

#### Git Workflow

- Write descriptive commit messages
- Keep commits atomic and focused
- Use present tense in commit messages (e.g., "Add feature" not "Added feature")
- Reference issues in commits when applicable

#### File Organization

- One component/module per file
- Group related files in directories
- Keep test files alongside source files or in a dedicated test directory
- Use clear, descriptive file names

### Testing Requirements

- Write tests for new functionality
- Maintain test coverage for critical paths
- Run tests before committing changes
- Use descriptive test names that explain the expected behavior

## Common Commands

Once the project is set up, common commands will typically include:

```bash
# Install dependencies
npm install        # or yarn install, pip install -r requirements.txt

# Run development server
npm run dev        # or python app.py, etc.

# Run tests
npm test           # or pytest, go test, etc.

# Build for production
npm run build      # or appropriate build command

# Lint code
npm run lint       # or eslint ., pylint src/, etc.

# Format code
npm run format     # or prettier --write ., black ., etc.
```

## Important Files to Create

When setting up this project, consider creating:

| File | Purpose |
|------|---------|
| `package.json` | Node.js dependencies and scripts |
| `tsconfig.json` | TypeScript configuration |
| `.eslintrc.js` | Linting rules |
| `.prettierrc` | Code formatting rules |
| `.gitignore` | Files to exclude from git |
| `.env.example` | Example environment variables |
| `jest.config.js` | Test configuration |

## AI Assistant Instructions

### Do

- Read existing code before making changes
- Follow established patterns in the codebase
- Write tests for new functionality
- Update documentation when adding features
- Use existing utilities and helpers
- Keep changes focused and atomic
- Commit changes with clear messages

### Don't

- Introduce breaking changes without discussion
- Skip tests for new features
- Leave commented-out code
- Hardcode configuration values
- Ignore error handling
- Create duplicate functionality

### When Exploring the Codebase

1. Start with README.md and this CLAUDE.md
2. Review package.json (when created) for scripts and dependencies
3. Examine the directory structure
4. Look at configuration files for project conventions
5. Read tests to understand expected behavior

### When Making Changes

1. Understand the existing code structure
2. Follow established patterns
3. Write or update tests
4. Update documentation if needed
5. Test changes locally
6. Commit with descriptive messages

## Environment Setup

Once the project has dependencies, setup will typically involve:

1. Clone the repository
2. Install dependencies
3. Set up environment variables
4. Run database migrations (if applicable)
5. Start development server

## Architecture Notes

*This section will be updated as the project architecture is defined.*

Key architectural decisions and patterns will be documented here, including:

- Design patterns used
- State management approach
- API structure
- Database schema design
- Authentication/authorization flow

## Troubleshooting

Common issues and solutions will be documented here as the project develops.

## Resources

- Project documentation: (to be added)
- API documentation: (to be added)
- Contributing guidelines: (to be added)

---

## Update History

| Date | Changes |
|------|---------|
| 2025-11-19 | Initial CLAUDE.md created |

---

*This document should be updated as the project evolves to reflect current structure, conventions, and best practices.*
