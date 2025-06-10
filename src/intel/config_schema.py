"""Configuration schema defining required and optional environment variables."""

from typing import Dict, List, Set

# Required environment variables that must be set
REQUIRED_ENV_VARS: Set[str] = {"DIR_X_API_TOKEN", "DIR_EMAIL_PASS", "DIR_TRANSCRIPT_API_KEY"}

# Optional environment variables with defaults
OPTIONAL_ENV_VARS: Dict[str, str] = {
    "DIR_OPENAI_API_KEY": "",
    "DIR_ANTHROPIC_API_KEY": "",
    "DIR_GOOGLE_API_KEY": "",
}

# Environment variable to config path mapping
ENV_VAR_MAPPING: Dict[str, str] = {
    "DIR_X_API_TOKEN": "auth.x_bearer_token",
    "DIR_EMAIL_PASS": "auth.imap_password",
    "DIR_TRANSCRIPT_API_KEY": "transcription.api_key",
    "DIR_OPENAI_API_KEY": "llm.api_key",
    "DIR_ANTHROPIC_API_KEY": "llm.api_key",
    "DIR_GOOGLE_API_KEY": "llm.api_key",
}


def get_missing_required_vars(env_vars: Dict[str, str]) -> List[str]:
    """Return list of missing required environment variables."""
    return [var for var in REQUIRED_ENV_VARS if not env_vars.get(var)]


def get_remediation_message(missing_vars: List[str]) -> str:
    """Generate helpful remediation message for missing environment variables."""
    if not missing_vars:
        return ""

    var_list = ", ".join(missing_vars)
    example_var = missing_vars[0]

    return (
        f"Missing required environment variables: {var_list}\n"
        f"Set them via:\n"
        f"  export {example_var}=<your_token>\n"
        f"Or add them to a .env file in the project root."
    )
