from core.logger import get_logger
from fastapi import FastAPI
from models.document import DocumentCreate

logger = get_logger("openapi")


def custom_openapi(app: FastAPI) -> None:  # noqa: C901
    """Customize the openapi schema"""
    if app.openapi_schema:
        return app.openapi_schema

    # generate normal OpenAPI schema
    openapi_schema = app._original_openapi()

    def add_schema(name: str, schema: dict) -> None:
        if name in openapi_schema["components"]["schemas"]:
            logger.warning(f"Schema {name} already exists in OpenAPI schema. Overwriting.")
        openapi_schema["components"]["schemas"][name] = schema

    # Inject custom schemas
    add_schema("DocumentCreate", DocumentCreate.model_json_schema(ref_template="#/components/schemas/{model}"))

    # Build the tags section dynamically if missing
    if "tags" not in openapi_schema:
        tag_names = set()
        for route in app.routes:
            if hasattr(route, "tags"):
                tag_names.update(route.tags)
        openapi_schema["tags"] = [{"name": name} for name in tag_names]

    # Sorts tags: Login first, Register second, WebSocket Events last, then alphabetically
    openapi_schema["tags"].sort(key=lambda x: (x["name"] != "Login", x["name"] != "Register", x["name"] == "WebSocket Events", x["name"]))
    
    # Inject the websocket testing route into the OpenAPI schema dynamically
    for route in app.routes:
        if hasattr(route, "path") and "/events" in route.path:
            for path, methods in openapi_schema["paths"].items():
                if path == route.path:
                    for _, details in methods.items():
                        if "description" in details:
                            details["description"] += "\n\n<iframe src='/docs/websocket' style='width: 100%; height: 600px; border: none;'></iframe>"
                        else:
                            details["description"] = "<iframe src='/docs/websocket' style='width: 100%; height: 600px; border: none;'></iframe>"

    # Add deepObject style to filter and sort params
    for _, methods in openapi_schema["paths"].items():
        for _, method in methods.items():
            parameters = method.get("parameters", [])
            for param in parameters:
                if param["name"] == "filter":
                    # set deepObject style
                    param["style"] = "deepObject"
                    param["explode"] = True
                    param["schema"] = {"type": "object", "properties": {}}
                    param["example"] = {"[field][operator]": "value"}
                if param["name"] == "sort":
                    # set deepObject style
                    param["style"] = "deepObject"
                    param["explode"] = True
                    param["schema"] = {"type": "object", "properties": {}}
                    param["example"] = {"[field1]": "asc", "[field2]": "desc"}

    return openapi_schema
