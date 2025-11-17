# Field Exclusion in Paginated Responses

## Overview

The filtering system now supports automatic exclusion of fields from API responses when those fields are used as filters. This optimization prevents redundant data in responses - for example, when filtering memberships by `user_id`, there's no need to include the full `user` object in each returned membership.

## How It Works

### 1. FilterMeta Configuration

Add `exclude` parameter to the `FilterMeta` definition in your filter model. The `exclude` parameter accepts:
- **Column/Relationship reference**: Exclude that specific field (e.g., `Membership.user`)
- **`True`**: Exclude the filter field itself (uses the dict key)
- **String**: Exclude the specified field name (legacy support)

```python
class MembershipFilter(BaseFilterModel):
    user_id: int = Field()
    group_id: str = Field()

    @classmethod
    def get_filter_metadata(cls) -> dict[str, FilterMeta]:
        return {
            "user_id": FilterMeta(
                field=Membership.user_id, 
                exclude=Membership.user  # Exclude 'user' relationship when filtering by user_id
            ),
            "group_id": FilterMeta(
                field=Membership.group_id, 
                exclude=Membership.group  # Exclude 'group' relationship when filtering by group_id
            ),
            "accepted": FilterMeta(
                field=Membership.accepted,
                exclude=True  # Exclude 'accepted' field itself (same as filter name)
            ),
        }
```

### 2. Automatic Tracking

When a filter is applied, the `PaginatedResource` dependency automatically:
- Detects which filters have `exclude_from_response=True`
- Collects the field names of active filters
- Adds them to the `excluded_fields` list in the paginated response

### 3. Response Handling

Use `ExcludableFieldsJSONResponse` in your endpoint to handle field exclusion:

```python
from util.response import ExcludableFieldsJSONResponse

@membership_router.get(
    "/", 
    response_model=Paginated[MembershipRead],
    response_class=ExcludableFieldsJSONResponse  # Add this
)
async def list_memberships(
    _: User = Authenticate([Guard.group_access()]),
    memberships: Paginated[Membership] = PaginatedResource(
        Membership, 
        MembershipFilter, 
        key_columns=[Membership.user_id, Membership.group_id]
    ),
) -> Paginated[MembershipRead]:
    return memberships
```

## Example Usage

### Request
```
GET /memberships?filter[user_id][==]=42
```

### Response
```json
{
  "data": [
    {
      "group": {
        "id": "abc123",
        "name": "My Group"
      },
      "permissions": ["READ", "WRITE"],
      "is_owner": false,
      "accepted": true
      // Note: 'user' object is excluded since we filtered by user_id
    }
  ],
  "total": 10,
  "offset": 0,
  "limit": 25,
  "filters": [{"field": "user_id", "operator": "==", "value": "42"}],
  "excluded_fields": ["user"]  // Metadata about excluded fields
}
```

## Benefits

1. **Reduced Payload Size**: Eliminates redundant data when filtering by specific fields
2. **Better Performance**: Less data serialization and network transfer
3. **Automatic**: No manual intervention needed once configured
4. **Transparent**: The `excluded_fields` array informs clients which fields were excluded

## Implementation Details

### Components

1. **FilterMeta.exclude**: Specifies which field to exclude (column reference, True, or string)
2. **FilterableField.exclude_field**: The resolved field name to exclude in the response
3. **Paginated.excluded_fields**: List of field names excluded from response
4. **ExcludableFieldsJSONResponse**: Custom response class that removes fields during serialization

### Response Validation

The `ExcludableFieldsJSONResponse` class handles field removal after Pydantic validation but before JSON serialization, avoiding validation errors for missing fields while maintaining type safety.

## When to Use

Use `exclude` parameter when:
- The filter field corresponds to a relationship (e.g., `user_id` → `Membership.user` object)
- The field value is known from the filter and doesn't need to be returned
- The excluded field would create redundant data in the response

Examples:
- `exclude=Membership.user` - Exclude the user relationship object
- `exclude=True` - Exclude the filter field itself
- `exclude="custom_field"` - Exclude a specific field by name (string)

Don't use it when:
- The field might have multiple values or variations
- The field is essential for client-side processing
- The exclusion would break client expectations

## Examples in Codebase

- **MembershipFilter**: Uses `exclude=Membership.user` and `exclude=Membership.group` to exclude relationships
- **GroupFilter**: Uses `exclude=True` for the `accepted` field to exclude itself
