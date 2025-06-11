# Configuration System Implementation Plan

This document outlines how to implement and integrate the `config.yaml` configuration system into the Daily Intelligence Report project.

## Goals

- Decide on an implementation for secret management. This can be via keychain (on mac), env variables or something else. We should consider cross-platform support as we want to eventually run some CI integration tests on github workflows, which are built against linux
- Outline a design for the implementation below that an AI coding assistant can implement with code assist frameworks.
- Decide on what level of testing should be included as part of this commit/feature work.

### Best Practices

- Keep secrets out of `config.yaml` — use `${...}` and environment variables at minimum.
- Fail fast with informative errors if config is incomplete or invalid.

## Implementation Plan

### Secret Management Strategy

**Decision**: Start with enhanced environment variable support for this feature branch. Future iterations will add keychain integration for local development convenience.

### Current Feature Branch: Environment Variable Enhancement

#### Phase 1: Enhanced Environment Variable Support
- [ ] Add validation for required environment variables in `config_loader.py`
- [ ] Implement `validate_config()` function to check for missing secrets
- [ ] Add detailed error messages with remediation tips when required environment variables are missing
- [ ] Create `config_schema.py` to define required vs optional configuration keys
- [ ] **CRITICAL**: Pin Pydantic version in `pyproject.toml` to avoid v1/v2 API drift

#### Phase 2: .env File Support for Local Development
- [ ] Add `python-dotenv` dependency to `pyproject.toml`
- [ ] Update `config_loader.py` to load `.env` file if present
- [ ] Add `.env.example` template file with consistent naming (e.g., `DIR_LLM_API_KEY`)
- [ ] Ensure `.env` is in `.gitignore`
- [ ] **CRITICAL**: Add `.pre-commit-config.yaml` with detect-secrets, yamllint, ruff hooks

#### Phase 3: Configuration Validation
- [ ] Create Pydantic models for configuration validation in `src/models/config.py`
- [ ] Implement strict typing for all config sections (storage, auth, llm, etc.)
- [ ] Add validation for API key formats, URL formats, file paths
- [ ] Implement config validation on startup with clear error messages
- [ ] **CRITICAL**: Keep config_loader.py thin - expose Settings.from_yaml() factory method
- [ ] **CRITICAL**: Return typed Settings object from validate_config(), not raw dict

#### Phase 4: Testing & Documentation
- [ ] Add unit tests for enhanced environment variable handling
- [ ] Add integration tests for config validation scenarios
- [ ] **CRITICAL**: Create `tests/test_env_precedence.py` with parametrized test matrix (with env, with .env, missing env, malformed env)
- [ ] Add tests for config validation and error handling
- [ ] Add CI dummy config test to catch missing secrets in GitHub Actions
- [ ] Update README with environment variable setup instructions
- [ ] Add `docs/configuration.md` with setup guide and common errors

### Technical Design for Current Branch

#### New Files to Create:
- `src/models/config.py` - Pydantic config models
- `tests/test_config_validation.py` - Config validation tests
- `.env.example` - Template for local development

#### Modified Files:
- `src/intel/config_loader.py` - Enhanced with validation and .env support
- `pyproject.toml` - Add python-dotenv and pydantic dependencies
- `config.yaml` - Add validation markers and better documentation
- `.gitignore` - Ensure .env is ignored

#### Configuration Resolution Order:
1. Environment variables (`${VAR_NAME}`)
2. .env file variables (if present)
3. Default values (if specified)
4. Fail with clear error message

### Testing Strategy

**Level**: Comprehensive unit and integration testing
- Unit tests for environment variable expansion and validation
- Integration tests for config loading with .env files
- Test configuration validation edge cases
- Mock missing environment variables for error testing

### Success Criteria for Current Branch

- [ ] All secrets removed from `config.yaml`
- [ ] Enhanced environment variable validation working
- [ ] .env file support for local development
- [ ] CI/CD pipeline compatibility maintained
- [ ] Clear error messages for missing configuration
- [ ] Backward compatibility with existing environment variable usage
- [ ] Documentation for environment variable setup

## Future Work (Next Feature Branches)

### Keychain Integration (Future)
- Add `keyring` dependency for cross-platform keychain access
- Extend config_loader to support keychain fallback: `${KEYCHAIN:service:username}`
- Implement keychain storage/retrieval functions
- Add CLI helper for storing secrets in keychain
- Cross-platform keychain testing
