import inspect

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
    for path, methods in openapi_schema["paths"].items():
        for method_name, method in methods.items():
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
            
            # Auto-inject guard exclusion descriptions
            if "description" in method:
                # Find the corresponding route to extract guards
                for route in app.routes:
                    if hasattr(route, "path") and hasattr(route, "methods"):
                        if route.path == path and method_name.upper() in route.methods:
                            # Check if route uses PaginatedResource with guards
                            guards = _extract_guards_from_route(route)
                            if guards:
                                guard_exclusions = []
                                for guard in guards:
                                    if hasattr(guard, "get_excluded_fields"):
                                        excluded = guard.get_excluded_fields()
                                        if excluded:
                                            guard_exclusions.extend(excluded)
                                
                                if guard_exclusions:
                                    excluded_fields = "', '".join(sorted(set(guard_exclusions)))
                                    exclusion_notice = (
                                        f"<br/><br/><strong>Field Exclusions:</strong> The following fields are always excluded from this endpoint's "
                                        f"responses due to access control rules: <code>{excluded_fields}</code>"
                                    )
                                    method["description"] = method["description"] + exclusion_notice
                            break

    return openapi_schema


def _extract_guards_from_route(route: object) -> list: # noqa: C901
    """Extract guards from a route's PaginatedResource dependency."""
    guards = []
    
    if not hasattr(route, "dependant"):
        return guards
    
    # Recursively search through dependencies
    def search_dependencies(dependant: object) -> None:
        if hasattr(dependant, "call"):
            # Check if this is a PaginatedResource by inspecting closure
            if hasattr(dependant.call, "__closure__") and dependant.call.__closure__:
                for cell in dependant.call.__closure__:
                    try:
                        if isinstance(cell.cell_contents, (list, tuple)):
                            # Check if it's a list of guards
                            for item in cell.cell_contents:
                                if hasattr(item, "get_excluded_fields"):
                                    guards.append(item)
                    except (AttributeError, ValueError):
                        pass
        
        # Recursively check dependencies
        if hasattr(dependant, "dependencies"):
            for dep in dependant.dependencies:
                search_dependencies(dep)
    
    search_dependencies(route.dependant)
    return guards
