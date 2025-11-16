"""Custom response utilities for handling dynamic field exclusion."""

from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ExcludableFieldsJSONResponse(JSONResponse):
    """JSON response that can exclude fields from nested objects in paginated data."""

    media_type = "application/json"

    def render(self, content: Any) -> bytes:  # noqa: ANN401
        """Render content, excluding specified fields from data items."""
        if isinstance(content, dict) and "excluded_fields" in content and "data" in content:
            excluded_fields = content.get("excluded_fields", [])
            if excluded_fields and isinstance(content["data"], list):
                cleaned_data = []
                for item in content["data"]:
                    if isinstance(item, dict):
                        cleaned_item = {k: v for k, v in item.items() if k not in excluded_fields}
                        cleaned_data.append(cleaned_item)
                    elif isinstance(item, BaseModel):
                        item_dict = item.model_dump()
                        cleaned_item = {k: v for k, v in item_dict.items() if k not in excluded_fields}
                        cleaned_data.append(cleaned_item)
                    else:
                        cleaned_data.append(item)
                content["data"] = cleaned_data
        
        return super().render(content)
