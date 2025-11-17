"""Generate TypeScript type mappings and exclusion maps from FilterMeta configuration."""
import sys
from pathlib import Path
from typing import Any
import inspect

# Add backend app to path
backend_path = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(backend_path))

import models.filter as filter_module
from models.filter import BaseFilterModel


def extract_field_name(exclude_value: Any) -> str | None:  # noqa: ANN401
    """Extract field name from exclude value (True, string, or Column/Relationship)."""
    if exclude_value is None:
        return None
    if exclude_value is True:
        return None
    if isinstance(exclude_value, str):
        return exclude_value
    if hasattr(exclude_value, "key"):
        return exclude_value.key
    if hasattr(exclude_value, "name"):
        return exclude_value.name
    return None


def discover_filter_models() -> list[type[BaseFilterModel]]:
    """Automatically discover all filter model classes in the filter module."""
    filter_models = []
    
    for name, obj in inspect.getmembers(filter_module):
        if (
            inspect.isclass(obj)
            and issubclass(obj, BaseFilterModel)
            and obj is not BaseFilterModel
            and hasattr(obj, "get_filter_metadata")
        ):
            filter_models.append(obj)
    
    return filter_models


def extract_base_name(filter_name: str) -> str | None:
    """Extract base name from filter model name (e.g., 'MembershipFilter' -> 'Membership')."""
    if filter_name.endswith("Filter"):
        return filter_name[:-6]
    return None


def generate_exclusion_maps() -> dict[str, dict[str, str]]:
    """Generate exclusion maps from all filter models."""
    filter_models = discover_filter_models()
    
    exclusion_data = {}
    
    for filter_class in filter_models:
            
        metadata = filter_class.get_filter_metadata()
        filter_exclusions = {}
        
        for field_name, filter_meta in metadata.items():
            if filter_meta.exclude:
                if filter_meta.exclude is True:
                    filter_exclusions[field_name] = field_name
                else:
                    excluded_field = extract_field_name(filter_meta.exclude)
                    if excluded_field:
                        filter_exclusions[field_name] = excluded_field
        
        if filter_exclusions:
            exclusion_data[filter_class.__name__] = filter_exclusions
    
    return exclusion_data


def write_combined_maps_file(
    filter_models: list[type[BaseFilterModel]], 
    exclusion_data: dict[str, dict[str, str]], 
    output_path: Path
) -> None:
    """Write both exclusion maps and filter type maps to a single TypeScript file."""
    ts_content = """/* tslint:disable */
/* eslint-disable */
/**
 * This file was automatically generated from backend filter models.
 * Do not modify it by hand - regenerate by running: pnpm run typegen
 */

import type * as Types from './types';

/**
 * Maps filter field names to the response fields they should exclude.
 * Only applies when using the '==' operator.
 */
export const ExclusionMaps = {
"""
    
    # Generate exclusion maps
    for filter_name, exclusions in sorted(exclusion_data.items()):
        ts_content += f"  {filter_name}: {{\n"
        for field, excluded in exclusions.items():
            ts_content += f"    {field}: '{excluded}',\n"
        ts_content += "  },\n"
    
    ts_content += "} as const;\n\n"
    ts_content += "export type ExclusionMaps = typeof ExclusionMaps;\n\n"
    
    # Generate GetFilterModel type mapping
    ts_content += """/**
 * Get the filter model type for a given read model type.
 * Auto-generated mapping: XxxRead -> XxxFilter
 */
export type GetFilterModel<T> = 
"""
    
    for filter_class in sorted(filter_models, key=lambda x: x.__name__):
        base_name = extract_base_name(filter_class.__name__)
        if base_name:
            ts_content += f"\tT extends Types.{base_name}Read ? Types.{filter_class.__name__} :\n"
    
    ts_content += "\tTypes.Filter;\n\n"
    
    # Generate FilterTypeToName mapping
    ts_content += """/**
 * Map from Filter types to their string names in ExclusionMaps.
 * Auto-generated from backend filter models.
 */
export type FilterTypeToName<T> = 
"""
    
    for filter_class in sorted(filter_models, key=lambda x: x.__name__):
        ts_content += f"\tT extends Types.{filter_class.__name__} ? '{filter_class.__name__}' :\n"
    
    ts_content += "\tnever;\n"
    
    output_path.write_text(ts_content)
    print(f"✅ Generated type maps: {output_path}")


if __name__ == "__main__":
    filter_models = discover_filter_models()
    exclusion_data = generate_exclusion_maps()
    
    frontend_api_path = Path(__file__).parent.parent.parent / "frontend" / "src" / "api"
    frontend_api_path.mkdir(parents=True, exist_ok=True)
    
    # Generate combined maps file
    maps_path = frontend_api_path / "maps.generated.ts"
    write_combined_maps_file(filter_models, exclusion_data, maps_path)
    
    print(f"\n✅ Successfully generated mappings for {len(filter_models)} filter models")
