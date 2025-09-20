import json
import re
import logging
from typing import Dict, Any, List, Tuple, Set

# Configure logging
logger = logging.getLogger(__name__)

def text_file_template(filename: str, variables: Dict[str, Any] = None) -> str:
    """
    Read a text file and safely substitute placeholders using Python .format().
    - Escapes ALL braces to avoid KeyError from LaTeX or examples.
    - Then selectively un-escapes placeholders that match provided variable keys.
    - Supports both {var} and {{var}} forms in source templates.
    """
    if variables is None:
        variables = {}

    try:
        with open(filename, "r", encoding="utf-8") as file:
            template = file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"The file '{filename}' was not found.")

    # First, escape all braces so non-placeholder braces don't break .format()
    escaped = template.replace("{", "{{").replace("}", "}}")

    # Then, un-escape placeholders that match keys in 'variables'
    # Handle both {var} and {{var}} written by authors.
    for key in variables.keys():
        escaped = escaped.replace("{{{{" + key + "}}}}", "{" + key + "}")
        escaped = escaped.replace("{{" + key + "}}", "{" + key + "}")

    try:
        formatted_text = escaped.format(**variables)
    except KeyError as e:
        missing_key = e.args[0]
        raise KeyError(f"Missing variable for placeholder: '{missing_key}'") from e

    return formatted_text
