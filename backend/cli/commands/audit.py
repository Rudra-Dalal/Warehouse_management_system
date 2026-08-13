from cli.client.api_client import make_request, APIError
from cli.ui.output import print_table, print_object
from cli.ui.errors import print_error_and_exit

def handle_audit_list(args) -> None:
    """Lists operational audit trail records with filters and pagination."""
    try:
        # Construct query filters dynamically from CLI arguments
        query_params = {
            "action": args.action,
            "entity_type": args.entity_type,
            "entity_id": args.entity_id,
            "user_id": args.user_id,
            "warehouse_code": args.warehouse_code,
            "reference_type": args.reference_type,
            "reference_id": args.reference_id,
            "success": args.success,
            "limit": args.limit,
            "offset": args.offset,
        }
        
        logs = make_request("GET", "/v1/audit", query_params=query_params)
        headers = ["ID", "Action", "Entity Type", "Entity ID", "User ID", "Success", "Created At"]
        rows = [
            [
                item.get("id"),
                item.get("action"),
                item.get("entity_type"),
                item.get("entity_id"),
                item.get("user_id"),
                item.get("success"),
                item.get("created_at"),
            ]
            for item in logs
        ]
        print_table(headers, rows)
    except APIError as e:
        print_error_and_exit(e)

def handle_audit_get(args) -> None:
    """Retrieves specific audit record details by string ObjectId."""
    try:
        log = make_request("GET", f"/v1/audit/{args.audit_id}")
        print_object(log)
    except APIError as e:
        print_error_and_exit(e)

def handle_audit_entity(args) -> None:
    """Retrieves audit trail history for a specific entity."""
    try:
        query_params = {
            "limit": args.limit,
            "offset": args.offset,
        }
        path = f"/v1/audit/entity/{args.entity_type}/{args.entity_id}"
        logs = make_request("GET", path, query_params=query_params)
        
        headers = ["ID", "Action", "Entity Type", "Entity ID", "User ID", "Success", "Created At"]
        rows = [
            [
                item.get("id"),
                item.get("action"),
                item.get("entity_type"),
                item.get("entity_id"),
                item.get("user_id"),
                item.get("success"),
                item.get("created_at"),
            ]
            for item in logs
        ]
        print_table(headers, rows)
    except APIError as e:
        print_error_and_exit(e)

def handle_audit_user(args) -> None:
    """Retrieves audit trail history for actions performed by a specific user."""
    try:
        query_params = {
            "limit": args.limit,
            "offset": args.offset,
        }
        path = f"/v1/audit/user/{args.user_id}"
        logs = make_request("GET", path, query_params=query_params)
        
        headers = ["ID", "Action", "Entity Type", "Entity ID", "User ID", "Success", "Created At"]
        rows = [
            [
                item.get("id"),
                item.get("action"),
                item.get("entity_type"),
                item.get("entity_id"),
                item.get("user_id"),
                item.get("success"),
                item.get("created_at"),
            ]
            for item in logs
        ]
        print_table(headers, rows)
    except APIError as e:
        print_error_and_exit(e)
