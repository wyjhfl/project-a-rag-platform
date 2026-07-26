"""Force network isolation for the test suite.

A developer's local .env may configure real LLM/embedding providers via
load_dotenv(override=False). Tests must stay deterministic and offline, so
pre-set the provider variables to empty strings before any app import; the
dotenv loader never overrides variables that already exist in the process
environment, and empty credentials keep every provider in fallback mode.
"""

import os

for _name in (
    "LLM_MODEL",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "EMBEDDING_MODEL",
    "EMBEDDING_API_KEY",
    "EMBEDDING_BASE_URL",
    "VISION_LLM_MODEL",
    "VISION_LLM_API_KEY",
    "VISION_LLM_BASE_URL",
):
    os.environ[_name] = ""
