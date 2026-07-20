import os
from django.conf import settings
from supabase import create_client, Client

_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase
    if _supabase is not None:
        return _supabase
    url = getattr(settings, "SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
    key = getattr(settings, "SUPABASE_KEY", os.getenv("SUPABASE_SERVICE_KEY", ""))
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment or Django settings"
        )
    _supabase = create_client(url, key)
    return _supabase


def supabase_get_clients():
    sb = get_supabase()
    return sb.table("clients").select("*").order("last_seen", desc=True).execute()


def supabase_get_client(key: str):
    sb = get_supabase()
    return sb.table("clients").select("*").eq("registration_key", key).execute()


def supabase_get_client_scans(key: str):
    sb = get_supabase()
    result = sb.table("clients").select("id").eq("registration_key", key).execute()
    if not result.data:
        return result
    client_id = result.data[0]["id"]
    return sb.table("scan_results").select("*").eq("client_id", client_id).order("created_at", desc=True).limit(50).execute()


def supabase_get_client_addons(key: str):
    sb = get_supabase()
    result = sb.table("clients").select("id").eq("registration_key", key).execute()
    if not result.data:
        return result
    client_id = result.data[0]["id"]
    return sb.table("addon_devices").select("*").eq("client_id", client_id).order("added_at", desc=True).execute()


def supabase_register_client(key: str, hostname: str, platform_name: str):
    sb = get_supabase()
    existing = sb.table("clients").select("id").eq("registration_key", key).execute()
    if existing.data:
        sb.table("clients").update({
            "hostname": hostname,
            "platform": platform_name,
            "status": "pending",
            "last_seen": "now()",
        }).eq("registration_key", key).execute()
        return {"status": "pending", "message": "Key already registered, waiting for approval"}
    sb.table("clients").insert({
        "registration_key": key,
        "hostname": hostname,
        "platform": platform_name,
        "status": "pending",
        "last_seen": "now()",
    }).execute()
    return {"status": "pending", "message": "Registration key sent, waiting for admin approval"}


def supabase_approve_client(key: str):
    sb = get_supabase()
    result = sb.table("clients").update({"approved": True, "status": "online"}).eq("registration_key", key).execute()
    if result.data:
        return {"status": "ok", "message": "Client approved"}
    return {"status": "error", "message": "Client not found"}


def supabase_ping_client(key: str, hostname: str):
    sb = get_supabase()
    sb.table("clients").update({
        "status": "online",
        "last_seen": "now()",
        "hostname": hostname,
    }).eq("registration_key", key).execute()
    return {"status": "ok"}


def supabase_delete_client(key: str):
    sb = get_supabase()
    sb.table("clients").delete().eq("registration_key", key).execute()
    return {"status": "ok"}


SERVER_REGISTRY_TABLE = "server_registry"


def register_server_in_registry(ip_address, port=80, protocol="http"):
    sb = get_supabase()
    sb.table(SERVER_REGISTRY_TABLE).upsert({
        "id": "admin",
        "ip_address": ip_address,
        "port": port,
        "protocol": protocol,
        "is_active": True,
        "updated_at": "now()",
    }, on_conflict="id").execute()
    return True


def get_server_from_registry():
    sb = get_supabase()
    result = (
        sb.table(SERVER_REGISTRY_TABLE)
        .select("ip_address,port,protocol,is_active")
        .eq("id", "admin")
        .execute()
    )
    return result.data[0] if result.data else None


def deactivate_server_in_registry():
    sb = get_supabase()
    sb.table(SERVER_REGISTRY_TABLE).update({
        "is_active": False,
        "updated_at": "now()",
    }).eq("id", "admin").execute()
    return True
