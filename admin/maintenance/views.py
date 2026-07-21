import logging
from datetime import timedelta
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone as tz
from django.db import models
from django.db.models import Count, Sum, Avg, Q, F
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from scanner_api.models import Asset, AssetAssignment, Department, Location, Employee
from .models import (
    MaintenanceRecord, MaintenanceHistory, MaintenanceDocument,
    WarrantyRecord, DowntimeRecord,
    SoftwareLicense, LicenseAssignment, LicenseHistory,
    ComplianceRecord, MaintenanceAlert,
)
from .serializers import (
    MaintenanceRecordSerializer, MaintenanceRecordListSerializer,
    MaintenanceHistorySerializer, MaintenanceDocumentSerializer,
    WarrantyRecordSerializer, DowntimeRecordSerializer,
    SoftwareLicenseSerializer, SoftwareLicenseListSerializer,
    LicenseAssignmentSerializer, LicenseHistorySerializer,
    ComplianceRecordSerializer, MaintenanceAlertSerializer,
    MaintenanceCreateSerializer, MaintenanceUpdateSerializer,
    MaintenanceStatusSerializer, MaintenanceApprovalSerializer,
    LicenseCreateSerializer, LicenseUpdateSerializer,
    LicenseAssignmentCreateSerializer,
    WarrantyCreateSerializer, DowntimeCreateSerializer,
    AlertActionSerializer,
)
from .alerts import (
    check_and_generate_alerts, acknowledge_alert, resolve_alert, dismiss_alert,
    acknowledge_compliance, resolve_compliance,
)

logger = logging.getLogger("maintenance")


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _record_maintenance_history(maintenance, action, description="", prev=None, new=None, request=None):
    MaintenanceHistory.objects.create(
        maintenance=maintenance,
        action=action,
        description=description,
        previous_value=prev or {},
        new_value=new or {},
        performed_by=request.user.username if request and request.user.is_authenticated else "system",
        ip_address=_client_ip(request) if request else None,
    )


def _record_license_history(license_obj, action, description="", prev=None, new=None, request=None):
    LicenseHistory.objects.create(
        license=license_obj,
        action=action,
        description=description,
        previous_value=prev or {},
        new_value=new or {},
        performed_by=request.user.username if request and request.user.is_authenticated else "system",
    )


def _mask_license_key(key):
    if not key:
        return ""
    parts = key.split("-")
    if len(parts) <= 1:
        if len(key) > 4:
            return "X" * (len(key) - 4) + key[-4:]
        return "X" * len(key)
    masked_parts = []
    for i, part in enumerate(parts):
        if i >= len(parts) - 1 and len(part) > 4:
            masked_parts.append("X" * (len(part) - 4) + part[-4:])
        else:
            masked_parts.append("X" * len(part))
    return "-".join(masked_parts)


# ═══════════════════════════════════════════════════════════════════════════════
# MAINTENANCE MANAGEMENT VIEWS
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class MaintenanceListView(APIView):
    def get(self, request):
        qs = MaintenanceRecord.objects.filter(deleted=False).select_related("asset", "department")
        search = request.query_params.get("search", "").strip()
        mtype = request.query_params.get("type", "").strip()
        mstatus = request.query_params.get("status", "").strip()
        priority = request.query_params.get("priority", "").strip()
        asset_id = request.query_params.get("asset", "").strip()
        department = request.query_params.get("department", "").strip()
        date_from = request.query_params.get("date_from", "").strip()
        date_to = request.query_params.get("date_to", "").strip()

        if search:
            qs = qs.filter(
                Q(maintenance_id__icontains=search) |
                Q(asset__asset_name__icontains=search) |
                Q(asset__asset_tag__icontains=search) |
                Q(vendor_name__icontains=search) |
                Q(technician__icontains=search) |
                Q(description__icontains=search)
            )
        if mtype:
            qs = qs.filter(maintenance_type=mtype)
        if mstatus:
            qs = qs.filter(status=mstatus)
        if priority:
            qs = qs.filter(priority=priority)
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        if department:
            qs = qs.filter(department_id=department)
        if date_from:
            qs = qs.filter(scheduled_date__gte=date_from)
        if date_to:
            qs = qs.filter(scheduled_date__lte=date_to)

        page_size = int(request.query_params.get("page_size", 50))
        page = int(request.query_params.get("page", 1))
        total = qs.count()
        start = (page - 1) * page_size
        records = qs[start:start + page_size]

        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if page_size else 1,
            "results": MaintenanceRecordListSerializer(records, many=True).data,
        })

    def post(self, request):
        serializer = MaintenanceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            asset = Asset.objects.get(id=data["asset"], deleted=False)
        except Asset.DoesNotExist:
            return Response({"status": "error", "message": "Asset not found"}, status=status.HTTP_404_NOT_FOUND)

        if asset.asset_status == "Disposed":
            return Response({"status": "error", "message": "Cannot schedule maintenance for disposed assets"},
                            status=status.HTTP_400_BAD_REQUEST)

        department = None
        if data.get("department"):
            try:
                department = Department.objects.get(id=data["department"], deleted=False)
            except Department.DoesNotExist:
                return Response({"status": "error", "message": "Department not found"}, status=status.HTTP_404_NOT_FOUND)

        maintenance = MaintenanceRecord.objects.create(
            asset=asset,
            asset_category_name=asset.category.name if asset.category else "",
            maintenance_type=data["maintenance_type"],
            status="Draft",
            approval_status="Pending",
            vendor_name=data.get("vendor_name", ""),
            vendor_contact=data.get("vendor_contact", ""),
            technician=data.get("technician", ""),
            description=data.get("description", ""),
            notes=data.get("notes", ""),
            scheduled_date=data.get("scheduled_date"),
            start_date=data.get("start_date"),
            completion_date=data.get("completion_date"),
            due_date=data.get("due_date"),
            estimated_cost=data.get("estimated_cost"),
            actual_cost=data.get("actual_cost"),
            downtime_hours=data.get("downtime_hours", 0),
            priority=data.get("priority", "Medium"),
            recurring=data.get("recurring", False),
            recurrence_interval_days=data.get("recurrence_interval_days", 0),
            department=department,
            created_by=request.user.username if request.user.is_authenticated else "system",
        )
        _record_maintenance_history(maintenance, "created",
                                    f"Maintenance {maintenance.maintenance_id} created for {asset.asset_name}",
                                    new=MaintenanceRecordSerializer(maintenance).data, request=request)
        return Response(MaintenanceRecordSerializer(maintenance).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class MaintenanceDetailView(APIView):
    def get(self, request, key):
        try:
            m = MaintenanceRecord.objects.select_related("asset", "department").get(id=key, deleted=False)
        except MaintenanceRecord.DoesNotExist:
            return Response({"status": "error", "message": "Maintenance record not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(MaintenanceRecordSerializer(m).data)

    def put(self, request, key):
        try:
            m = MaintenanceRecord.objects.get(id=key, deleted=False)
        except MaintenanceRecord.DoesNotExist:
            return Response({"status": "error", "message": "Maintenance record not found"}, status=status.HTTP_404_NOT_FOUND)

        if m.status == "Completed":
            return Response({"status": "error", "message": "Completed maintenance records are immutable"},
                            status=status.HTTP_400_BAD_REQUEST)

        prev = MaintenanceRecordSerializer(m).data
        serializer = MaintenanceUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "department" in data:
            dept_id = data.pop("department")
            if dept_id:
                try:
                    m.department = Department.objects.get(id=dept_id, deleted=False)
                except Department.DoesNotExist:
                    return Response({"status": "error", "message": "Department not found"}, status=status.HTTP_404_NOT_FOUND)
            else:
                m.department = None

        for field, value in data.items():
            setattr(m, field, value)
        m.save()

        _record_maintenance_history(m, "updated", "Maintenance record updated",
                                    prev=prev, new=MaintenanceRecordSerializer(m).data, request=request)
        return Response(MaintenanceRecordSerializer(m).data)

    def delete(self, request, key):
        try:
            m = MaintenanceRecord.objects.get(id=key, deleted=False)
        except MaintenanceRecord.DoesNotExist:
            return Response({"status": "error", "message": "Maintenance record not found"}, status=status.HTTP_404_NOT_FOUND)
        if m.status == "Completed":
            return Response({"status": "error", "message": "Completed maintenance cannot be deleted"},
                            status=status.HTTP_400_BAD_REQUEST)
        m.delete()
        _record_maintenance_history(m, "deleted", "Maintenance record deleted", request=request)
        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class MaintenanceStatusView(APIView):
    def post(self, request, key):
        try:
            m = MaintenanceRecord.objects.get(id=key, deleted=False)
        except MaintenanceRecord.DoesNotExist:
            return Response({"status": "error", "message": "Maintenance record not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = MaintenanceStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_status = data["status"]
        notes = data.get("notes", "")
        prev_status = m.status
        prev = MaintenanceRecordSerializer(m).data

        VALID_TRANSITIONS = {
            "Draft": ["Pending Approval", "Cancelled"],
            "Pending Approval": ["Approved", "Cancelled"],
            "Approved": ["Scheduled", "Cancelled"],
            "Scheduled": ["In Progress", "Cancelled"],
            "In Progress": ["Completed", "Waiting Parts"],
            "Waiting Parts": ["In Progress", "Cancelled"],
            "Completed": [],
            "Cancelled": [],
            "Overdue": ["In Progress", "Cancelled"],
        }
        allowed = VALID_TRANSITIONS.get(prev_status, [])
        if new_status not in allowed:
            return Response(
                {"status": "error", "message": f"Cannot transition from '{prev_status}' to '{new_status}'. Allowed: {', '.join(allowed) if allowed else 'none'}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        m.status = new_status
        if new_status == "In Progress" and not m.start_date:
            m.start_date = tz.now().date()
        if new_status == "Completed":
            m.completion_date = tz.now().date()
            if m.asset:
                valid, msg = Asset.validate_status_transition(m.asset.asset_status, "Available")
                if valid:
                    m.asset.asset_status = "Available"
                    m.asset.save(update_fields=["asset_status", "updated_at"])
        m.save(update_fields=["status", "start_date", "completion_date", "updated_at"])

        _record_maintenance_history(m, f"status_changed_{new_status}",
                                    f"Status changed from {prev_status} to {new_status}. {notes}",
                                    prev={"status": prev_status}, new={"status": new_status}, request=request)
        return Response(MaintenanceRecordSerializer(m).data)


@method_decorator(csrf_exempt, name="dispatch")
class MaintenanceApprovalView(APIView):
    def post(self, request, key):
        try:
            m = MaintenanceRecord.objects.get(id=key, deleted=False)
        except MaintenanceRecord.DoesNotExist:
            return Response({"status": "error", "message": "Maintenance record not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = MaintenanceApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        prev_approval = m.approval_status
        m.approval_status = data["approval_status"]
        m.approved_by = request.user.username if request.user.is_authenticated else "system"

        if data["approval_status"] == "Approved":
            m.status = "Approved"
        elif data["approval_status"] == "Rejected":
            m.status = "Cancelled"

        m.save(update_fields=["approval_status", "approved_by", "status", "updated_at"])

        _record_maintenance_history(m, f"approval_{data['approval_status'].lower()}",
                                    f"Approval status changed to {data['approval_status']}. {data.get('notes', '')}",
                                    prev={"approval_status": prev_approval},
                                    new={"approval_status": data["approval_status"]}, request=request)
        return Response(MaintenanceRecordSerializer(m).data)


@method_decorator(csrf_exempt, name="dispatch")
class MaintenanceDocumentUploadView(APIView):
    def post(self, request, key):
        try:
            m = MaintenanceRecord.objects.get(id=key, deleted=False)
        except MaintenanceRecord.DoesNotExist:
            return Response({"status": "error", "message": "Maintenance record not found"}, status=status.HTTP_404_NOT_FOUND)

        if "file" not in request.FILES:
            return Response({"status": "error", "message": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        f = request.FILES["file"]
        if f.size > 10 * 1024 * 1024:
            return Response({"status": "error", "message": "File too large (max 10MB)"}, status=status.HTTP_400_BAD_REQUEST)

        import base64
        file_data = base64.b64encode(f.read()).decode("utf-8")

        doc = MaintenanceDocument.objects.create(
            maintenance=m,
            name=f.name,
            file_data=file_data,
            file_type=f.content_type,
            file_size=f.size,
            uploaded_by=request.user.username if request.user.is_authenticated else "system",
        )
        _record_maintenance_history(m, "document_uploaded", f"Document '{f.name}' uploaded", request=request)
        return Response(MaintenanceDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


# ── Warranty Views ──────────────────────────────────────────────────────────


@method_decorator(csrf_exempt, name="dispatch")
class WarrantyListView(APIView):
    def get(self, request):
        qs = WarrantyRecord.objects.filter(deleted=False).select_related("asset")
        search = request.query_params.get("search", "").strip()
        s = request.query_params.get("status", "").strip()
        expiring = request.query_params.get("expiring", "").strip()

        if search:
            qs = qs.filter(
                Q(warranty_id__icontains=search) |
                Q(asset__asset_name__icontains=search) |
                Q(warranty_provider__icontains=search) |
                Q(contract_number__icontains=search)
            )
        if s:
            qs = qs.filter(status=s)
        if expiring == "true":
            today = tz.now().date()
            soon = today + timedelta(days=30)
            qs = qs.filter(warranty_end__lte=soon, warranty_end__gte=today)

        page_size = int(request.query_params.get("page_size", 50))
        page = int(request.query_params.get("page", 1))
        total = qs.count()
        start = (page - 1) * page_size
        records = qs[start:start + page_size]

        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if page_size else 1,
            "results": WarrantyRecordSerializer(records, many=True).data,
        })

    def post(self, request):
        serializer = WarrantyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            asset = Asset.objects.get(id=data["asset"], deleted=False)
        except Asset.DoesNotExist:
            return Response({"status": "error", "message": "Asset not found"}, status=status.HTTP_404_NOT_FOUND)

        if data["warranty_end"] <= data["warranty_start"]:
            return Response({"status": "error", "message": "Warranty end date must be after start date"},
                            status=status.HTTP_400_BAD_REQUEST)

        warranty = WarrantyRecord.objects.create(
            asset=asset,
            warranty_start=data["warranty_start"],
            warranty_end=data["warranty_end"],
            warranty_provider=data["warranty_provider"],
            contract_number=data.get("contract_number", ""),
            amc_details=data.get("amc_details", ""),
            support_contact_name=data.get("support_contact_name", ""),
            support_contact_email=data.get("support_contact_email", ""),
            support_contact_phone=data.get("support_contact_phone", ""),
            coverage_type=data.get("coverage_type", "Full"),
            notes=data.get("notes", ""),
            cost=data.get("cost"),
        )
        return Response(WarrantyRecordSerializer(warranty).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class WarrantyDetailView(APIView):
    def get(self, request, key):
        try:
            w = WarrantyRecord.objects.select_related("asset").get(id=key, deleted=False)
        except WarrantyRecord.DoesNotExist:
            return Response({"status": "error", "message": "Warranty record not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(WarrantyRecordSerializer(w).data)

    def delete(self, request, key):
        try:
            w = WarrantyRecord.objects.get(id=key, deleted=False)
        except WarrantyRecord.DoesNotExist:
            return Response({"status": "error", "message": "Warranty record not found"}, status=status.HTTP_404_NOT_FOUND)
        w.delete()
        return Response({"status": "ok"})


# ── Downtime Views ──────────────────────────────────────────────────────────


@method_decorator(csrf_exempt, name="dispatch")
class DowntimeListView(APIView):
    def get(self, request):
        qs = DowntimeRecord.objects.select_related("asset", "maintenance")
        asset_id = request.query_params.get("asset", "").strip()
        reason = request.query_params.get("reason", "").strip()

        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        if reason:
            qs = qs.filter(reason=reason)

        limit = int(request.query_params.get("limit", 100))
        return Response(DowntimeRecordSerializer(qs[:limit], many=True).data)

    def post(self, request):
        serializer = DowntimeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            asset = Asset.objects.get(id=data["asset"], deleted=False)
        except Asset.DoesNotExist:
            return Response({"status": "error", "message": "Asset not found"}, status=status.HTTP_404_NOT_FOUND)

        maintenance = None
        if data.get("maintenance"):
            try:
                maintenance = MaintenanceRecord.objects.get(id=data["maintenance"], deleted=False)
            except MaintenanceRecord.DoesNotExist:
                return Response({"status": "error", "message": "Maintenance record not found"}, status=status.HTTP_404_NOT_FOUND)

        record = DowntimeRecord.objects.create(
            asset=asset,
            maintenance=maintenance,
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            reason=data.get("reason", "Maintenance"),
            description=data.get("description", ""),
        )
        if record.end_time:
            record.save()
        return Response(DowntimeRecordSerializer(record).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class DowntimeEndView(APIView):
    def post(self, request, key):
        try:
            record = DowntimeRecord.objects.get(id=key)
        except DowntimeRecord.DoesNotExist:
            return Response({"status": "error", "message": "Downtime record not found"}, status=status.HTTP_404_NOT_FOUND)
        if record.end_time:
            return Response({"status": "error", "message": "Downtime already ended"}, status=status.HTTP_400_BAD_REQUEST)
        record.end_time = tz.now()
        record.save()
        return Response(DowntimeRecordSerializer(record).data)


# ═══════════════════════════════════════════════════════════════════════════════
# SOFTWARE LICENSE MANAGEMENT VIEWS
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class LicenseListView(APIView):
    def get(self, request):
        qs = SoftwareLicense.objects.filter(deleted=False).select_related("department")
        search = request.query_params.get("search", "").strip()
        ltype = request.query_params.get("type", "").strip()
        lstatus = request.query_params.get("status", "").strip()
        department = request.query_params.get("department", "").strip()
        expiring = request.query_params.get("expiring", "").strip()

        if search:
            qs = qs.filter(
                Q(license_id__icontains=search) |
                Q(software_name__icontains=search) |
                Q(vendor__icontains=search) |
                Q(product_edition__icontains=search) |
                Q(license_key_masked__icontains=search)
            )
        if ltype:
            qs = qs.filter(license_type=ltype)
        if lstatus:
            qs = qs.filter(status=lstatus)
        if department:
            qs = qs.filter(department_id=department)
        if expiring == "true":
            today = tz.now().date()
            soon = today + timedelta(days=30)
            qs = qs.filter(expiration_date__lte=soon, expiration_date__gte=today)

        page_size = int(request.query_params.get("page_size", 50))
        page = int(request.query_params.get("page", 1))
        total = qs.count()
        start = (page - 1) * page_size
        records = qs[start:start + page_size]

        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if page_size else 1,
            "results": SoftwareLicenseListSerializer(records, many=True).data,
        })

    def post(self, request):
        serializer = LicenseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        license_key = data.get("license_key", "")
        if license_key:
            from django.db import IntegrityError
            try:
                existing = SoftwareLicense.objects.filter(license_key_encrypted=license_key, deleted=False)
                if existing.exists():
                    return Response({"status": "error", "message": "A license with this key already exists"},
                                    status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                pass

        department = None
        if data.get("department"):
            try:
                department = Department.objects.get(id=data["department"], deleted=False)
            except Department.DoesNotExist:
                return Response({"status": "error", "message": "Department not found"}, status=status.HTTP_404_NOT_FOUND)

        seats = data.get("purchased_seats", 1)
        if seats < 1:
            return Response({"status": "error", "message": "Purchased seats must be at least 1"},
                            status=status.HTTP_400_BAD_REQUEST)

        lic = SoftwareLicense.objects.create(
            software_name=data["software_name"],
            vendor=data.get("vendor", ""),
            product_edition=data.get("product_edition", ""),
            version=data.get("version", ""),
            license_key_encrypted=license_key,
            license_key_masked=_mask_license_key(license_key),
            license_type=data.get("license_type", "Per User"),
            purchased_seats=seats,
            purchase_date=data.get("purchase_date"),
            expiration_date=data.get("expiration_date"),
            renewal_date=data.get("renewal_date"),
            cost=data.get("cost"),
            status="Active" if data.get("expiration_date") else "Draft",
            department=department,
            notes=data.get("notes", ""),
        )
        _record_license_history(lic, "created", f"License {lic.license_id} created for {lic.software_name}",
                                new=SoftwareLicenseSerializer(lic).data, request=request)
        return Response(SoftwareLicenseSerializer(lic).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class LicenseDetailView(APIView):
    def get(self, request, key):
        try:
            lic = SoftwareLicense.objects.select_related("department").get(id=key, deleted=False)
        except SoftwareLicense.DoesNotExist:
            return Response({"status": "error", "message": "License not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(SoftwareLicenseSerializer(lic).data)

    def put(self, request, key):
        try:
            lic = SoftwareLicense.objects.get(id=key, deleted=False)
        except SoftwareLicense.DoesNotExist:
            return Response({"status": "error", "message": "License not found"}, status=status.HTTP_404_NOT_FOUND)

        if lic.status == "Archived":
            return Response({"status": "error", "message": "Archived licenses are read-only"},
                            status=status.HTTP_400_BAD_REQUEST)

        prev = SoftwareLicenseSerializer(lic).data
        serializer = LicenseUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "license_key" in data:
            new_key = data.pop("license_key")
            if new_key:
                dup = SoftwareLicense.objects.filter(license_key_encrypted=new_key, deleted=False).exclude(id=key)
                if dup.exists():
                    return Response({"status": "error", "message": "A license with this key already exists"},
                                    status=status.HTTP_400_BAD_REQUEST)
                lic.license_key_encrypted = new_key
                lic.license_key_masked = _mask_license_key(new_key)

        if "department" in data:
            dept_id = data.pop("department")
            if dept_id:
                try:
                    lic.department = Department.objects.get(id=dept_id, deleted=False)
                except Department.DoesNotExist:
                    return Response({"status": "error", "message": "Department not found"}, status=status.HTTP_404_NOT_FOUND)
            else:
                lic.department = None

        for field, value in data.items():
            setattr(lic, field, value)
        lic.save()

        _record_license_history(lic, "updated", "License details updated",
                                prev=prev, new=SoftwareLicenseSerializer(lic).data, request=request)
        return Response(SoftwareLicenseSerializer(lic).data)

    def delete(self, request, key):
        try:
            lic = SoftwareLicense.objects.get(id=key, deleted=False)
        except SoftwareLicense.DoesNotExist:
            return Response({"status": "error", "message": "License not found"}, status=status.HTTP_404_NOT_FOUND)
        lic.delete()
        _record_license_history(lic, "deleted", "License deleted", request=request)
        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class LicenseArchiveView(APIView):
    def post(self, request, key):
        try:
            lic = SoftwareLicense.objects.get(id=key, deleted=False)
        except SoftwareLicense.DoesNotExist:
            return Response({"status": "error", "message": "License not found"}, status=status.HTTP_404_NOT_FOUND)
        lic.status = "Archived"
        lic.save(update_fields=["status", "updated_at"])
        _record_license_history(lic, "archived", "License archived", request=request)
        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class LicenseAssignView(APIView):
    def post(self, request):
        serializer = LicenseAssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            lic = SoftwareLicense.objects.get(id=data["license"], deleted=False)
        except SoftwareLicense.DoesNotExist:
            return Response({"status": "error", "message": "License not found"}, status=status.HTTP_404_NOT_FOUND)

        if lic.status == "Archived":
            return Response({"status": "error", "message": "Cannot assign archived licenses"},
                            status=status.HTTP_400_BAD_REQUEST)

        if lic.seats_used >= lic.purchased_seats:
            return Response({"status": "error", "message": "No seats available. All seats are in use."},
                            status=status.HTTP_400_BAD_REQUEST)

        assignable_type = data["assignable_type"]
        asset = None
        employee = None
        department = None

        if assignable_type == "Asset":
            try:
                asset = Asset.objects.get(id=data["asset"], deleted=False)
            except (Asset.DoesNotExist, KeyError):
                return Response({"status": "error", "message": "Asset not found"}, status=status.HTTP_404_NOT_FOUND)
        elif assignable_type == "Employee":
            try:
                employee = Employee.objects.get(id=data["employee"], deleted=False)
            except (Employee.DoesNotExist, KeyError):
                return Response({"status": "error", "message": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        elif assignable_type == "Department":
            try:
                department = Department.objects.get(id=data["department"], deleted=False)
            except (Department.DoesNotExist, KeyError):
                return Response({"status": "error", "message": "Department not found"}, status=status.HTTP_404_NOT_FOUND)

        assignment = LicenseAssignment.objects.create(
            license=lic,
            assignable_type=assignable_type,
            asset=asset,
            employee=employee,
            department=department,
            assigned_by=request.user.username if request.user.is_authenticated else "system",
            notes=data.get("notes", ""),
        )
        lic.seats_used = F("seats_used") + 1
        lic.save(update_fields=["seats_used"])
        lic.refresh_from_db()

        _record_license_history(lic, "assigned", f"License assigned to {assignable_type}",
                                new={"assignable_type": assignable_type, "assignment_id": str(assignment.id)},
                                request=request)
        return Response(LicenseAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class LicenseRemoveAssignmentView(APIView):
    def post(self, request, key):
        try:
            assignment = LicenseAssignment.objects.get(id=key, is_active=True)
        except LicenseAssignment.DoesNotExist:
            return Response({"status": "error", "message": "Active assignment not found"}, status=status.HTTP_404_NOT_FOUND)

        assignment.is_active = False
        assignment.removal_date = tz.now().date()
        assignment.notes = request.data.get("notes", assignment.notes)
        assignment.save(update_fields=["is_active", "removal_date", "notes"])

        lic = assignment.license
        if lic.seats_used > 0:
            lic.seats_used = F("seats_used") - 1
            lic.save(update_fields=["seats_used"])
            lic.refresh_from_db()

        _record_license_history(lic, "unassigned", f"License unassigned from {assignment.assignable_type}",
                                request=request)
        return Response({"status": "ok"})


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE & ALERTS VIEWS
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class ComplianceListView(APIView):
    def get(self, request):
        qs = ComplianceRecord.objects.all()
        category = request.query_params.get("category", "").strip()
        s = request.query_params.get("status", "").strip()
        severity = request.query_params.get("severity", "").strip()

        if category:
            qs = qs.filter(category=category)
        if s:
            qs = qs.filter(status=s)
        if severity:
            qs = qs.filter(severity=severity)

        limit = int(request.query_params.get("limit", 100))
        return Response(ComplianceRecordSerializer(qs[:limit], many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class ComplianceActionView(APIView):
    def post(self, request, key):
        serializer = AlertActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        if action == "acknowledge":
            ok = acknowledge_compliance(key)
        elif action == "resolve":
            ok = resolve_compliance(key)
        elif action == "dismiss":
            try:
                record = ComplianceRecord.objects.get(id=key, status__in=("active", "acknowledged"))
                record.status = "dismissed"
                record.save(update_fields=["status", "updated_at"])
                ok = True
            except ComplianceRecord.DoesNotExist:
                ok = False
        else:
            return Response({"status": "error", "message": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        if not ok:
            return Response({"status": "error", "message": "Record not found or invalid state"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({"status": "ok"})


@method_decorator(csrf_exempt, name="dispatch")
class MaintenanceAlertListView(APIView):
    def get(self, request):
        qs = MaintenanceAlert.objects.all()
        category = request.query_params.get("category", "").strip()
        s = request.query_params.get("status", "").strip()
        severity = request.query_params.get("severity", "").strip()

        if category:
            qs = qs.filter(category=category)
        if s:
            qs = qs.filter(status=s)
        if severity:
            qs = qs.filter(severity=severity)

        limit = int(request.query_params.get("limit", 100))
        return Response(MaintenanceAlertSerializer(qs[:limit], many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class MaintenanceAlertActionView(APIView):
    def post(self, request, key):
        serializer = AlertActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        if action == "acknowledge":
            ok = acknowledge_alert(key)
        elif action == "resolve":
            ok = resolve_alert(key)
        elif action == "dismiss":
            ok = dismiss_alert(key)
        else:
            return Response({"status": "error", "message": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        if not ok:
            return Response({"status": "error", "message": "Alert not found or invalid state"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({"status": "ok"})


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD & ANALYTICS VIEWS
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class MaintenanceDashboardView(APIView):
    def get(self, request):
        today = tz.now().date()
        upcoming_30 = today + timedelta(days=30)

        total_maintenance = MaintenanceRecord.objects.filter(deleted=False).count()
        upcoming = MaintenanceRecord.objects.filter(
            deleted=False,
            scheduled_date__lte=upcoming_30,
            scheduled_date__gte=today,
            status__in=("Approved", "Scheduled"),
        ).count()
        overdue = MaintenanceRecord.objects.filter(
            deleted=False,
            status__in=("Scheduled", "In Progress", "Waiting Parts"),
            due_date__lt=today,
        ).count()
        in_progress = MaintenanceRecord.objects.filter(
            deleted=False, status="In Progress"
        ).count()
        assets_under_repair = MaintenanceRecord.objects.filter(
            deleted=False, status__in=("In Progress", "Waiting Parts")
        ).values("asset").distinct().count()

        monthly_cost = MaintenanceRecord.objects.filter(
            deleted=False,
            completion_date__year=today.year,
            completion_date__month=today.month,
            actual_cost__isnull=False,
        ).aggregate(total=Sum("actual_cost"))["total"] or 0

        total_cost_ytd = MaintenanceRecord.objects.filter(
            deleted=False,
            completion_date__year=today.year,
            actual_cost__isnull=False,
        ).aggregate(total=Sum("actual_cost"))["total"] or 0

        warranty_expiring = WarrantyRecord.objects.filter(
            deleted=False,
            warranty_end__lte=upcoming_30,
            warranty_end__gte=today,
            status="Active",
        ).count()

        total_downtime_hours = DowntimeRecord.objects.filter(
            start_time__year=today.year,
            start_time__month=today.month,
        ).aggregate(total=Sum("duration_hours"))["total"] or 0

        active_alerts = MaintenanceAlert.objects.filter(status="active").count()
        critical_alerts = MaintenanceAlert.objects.filter(status="active", severity="critical").count()

        by_type = dict(
            MaintenanceRecord.objects.filter(deleted=False).values_list("maintenance_type")
            .annotate(c=Count("id")).values_list("maintenance_type", "c")
        )

        by_status = dict(
            MaintenanceRecord.objects.filter(deleted=False).values_list("status")
            .annotate(c=Count("id")).values_list("status", "c")
        )

        by_priority = dict(
            MaintenanceRecord.objects.filter(deleted=False).values_list("priority")
            .annotate(c=Count("id")).values_list("priority", "c")
        )

        recent = MaintenanceRecordListSerializer(
            MaintenanceRecord.objects.filter(deleted=False).order_by("-created_at")[:10], many=True
        ).data

        recent_alerts = MaintenanceAlertSerializer(
            MaintenanceAlert.objects.order_by("-created_at")[:10], many=True
        ).data

        return Response({
            "total_maintenance": total_maintenance,
            "upcoming_maintenance": upcoming,
            "overdue_maintenance": overdue,
            "in_progress_maintenance": in_progress,
            "assets_under_repair": assets_under_repair,
            "monthly_maintenance_cost": float(monthly_cost),
            "year_to_date_cost": float(total_cost_ytd),
            "warranty_expiring": warranty_expiring,
            "monthly_downtime_hours": float(total_downtime_hours),
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "by_type": by_type,
            "by_status": by_status,
            "by_priority": by_priority,
            "recent_maintenance": recent,
            "recent_alerts": recent_alerts,
        })


@method_decorator(csrf_exempt, name="dispatch")
class MaintenanceCostTrendView(APIView):
    def get(self, request):
        months = int(request.query_params.get("months", 12))
        today = tz.now().date()
        trend = []
        for i in range(months):
            month_date = (today - timedelta(days=30 * (months - 1 - i)))
            month_start = month_date.replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)

            cost = MaintenanceRecord.objects.filter(
                deleted=False,
                completion_date__gte=month_start,
                completion_date__lt=month_end,
                actual_cost__isnull=False,
            ).aggregate(total=Sum("actual_cost"))["total"] or 0

            count = MaintenanceRecord.objects.filter(
                deleted=False,
                completion_date__gte=month_start,
                completion_date__lt=month_end,
            ).count()

            trend.append({
                "month": month_start.strftime("%Y-%m"),
                "cost": float(cost),
                "count": count,
            })
        return Response(trend)


@method_decorator(csrf_exempt, name="dispatch")
class VendorPerformanceView(APIView):
    def get(self, request):
        vendors = MaintenanceRecord.objects.filter(
            deleted=False, vendor_name__isnull=False
        ).exclude(vendor_name="").values("vendor_name").annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(status="Completed")),
            avg_cost=Avg("actual_cost"),
        ).order_by("-total")[:20]

        vendor_list = []
        for v in vendors:
            completion_rate = round((v["completed"] / v["total"] * 100), 1) if v["total"] else 0
            vendor_list.append({
                "vendor_name": v["vendor_name"],
                "total_maintenance": v["total"],
                "completed": v["completed"],
                "completion_rate": completion_rate,
                "avg_cost": float(v["avg_cost"]) if v["avg_cost"] else 0,
            })

        return Response(vendor_list)


@method_decorator(csrf_exempt, name="dispatch")
class AssetFailureRateView(APIView):
    def get(self, request):
        assets = Asset.objects.filter(deleted=False).annotate(
            maintenance_count=Count("maintenance_records", filter=~Q(maintenance_records__deleted=True)),
            failure_count=Count("maintenance_records", filter=Q(
                maintenance_records__maintenance_type__in=("Corrective", "Repair", "Emergency"),
                maintenance_records__deleted=False,
            )),
        ).filter(maintenance_count__gt=0).order_by("-failure_count")[:20]

        result = []
        for a in assets:
            failure_rate = round((a.failure_count / a.maintenance_count * 100), 1) if a.maintenance_count else 0
            result.append({
                "asset_id": str(a.id),
                "asset_name": a.asset_name,
                "asset_tag": a.asset_tag,
                "total_maintenance": a.maintenance_count,
                "failures": a.failure_count,
                "failure_rate": failure_rate,
            })

        return Response(result)


@method_decorator(csrf_exempt, name="dispatch")
class DowntimeAnalyticsView(APIView):
    def get(self, request):
        today = tz.now().date()
        months = int(request.query_params.get("months", 12))

        total_downtime = DowntimeRecord.objects.filter(
            start_time__year=today.year
        ).aggregate(total=Sum("duration_hours"))["total"] or 0

        avg_downtime = DowntimeRecord.objects.filter(
            start_time__year=today.year
        ).aggregate(avg=Avg("duration_hours"))["avg"] or 0

        by_reason = dict(
            DowntimeRecord.objects.filter(start_time__year=today.year)
            .values_list("reason")
            .annotate(c=Count("id"), total_hrs=Sum("duration_hours"))
            .values_list("reason", None)
        )
        by_reason_list = []
        for d in DowntimeRecord.objects.filter(start_time__year=today.year).values("reason").annotate(
            c=Count("id"), total_hrs=Sum("duration_hours")
        ):
            by_reason_list.append({
                "reason": d["reason"],
                "count": d["c"],
                "total_hours": float(d["total_hrs"] or 0),
            })

        trend = []
        for i in range(months):
            month_date = (today - timedelta(days=30 * (months - 1 - i)))
            month_start = month_date.replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)

            hours = DowntimeRecord.objects.filter(
                start_time__gte=month_start,
                start_time__lt=month_end,
            ).aggregate(total=Sum("duration_hours"))["total"] or 0

            trend.append({
                "month": month_start.strftime("%Y-%m"),
                "hours": float(hours),
            })

        asset_downtime = DowntimeRecord.objects.filter(
            start_time__year=today.year
        ).values("asset__asset_name", "asset__asset_tag").annotate(
            total_hours=Sum("duration_hours"),
            count=Count("id"),
        ).order_by("-total_hours")[:10]

        return Response({
            "total_downtime_hours": float(total_downtime),
            "avg_downtime_hours": float(avg_downtime),
            "by_reason": by_reason_list,
            "trend": trend,
            "top_assets": list(asset_downtime),
        })


# ═══════════════════════════════════════════════════════════════════════════════
# LICENSE ANALYTICS VIEWS
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class LicenseDashboardView(APIView):
    def get(self, request):
        today = tz.now().date()
        upcoming_30 = today + timedelta(days=30)

        total_licenses = SoftwareLicense.objects.filter(deleted=False).count()
        active_licenses = SoftwareLicense.objects.filter(deleted=False, status="Active").count()
        expired_licenses = SoftwareLicense.objects.filter(deleted=False, status="Expired").count()
        expiring_soon = SoftwareLicense.objects.filter(
            deleted=False,
            expiration_date__lte=upcoming_30,
            expiration_date__gte=today,
            status__in=("Active", "Draft"),
        ).count()

        total_seats = SoftwareLicense.objects.filter(deleted=False).aggregate(
            total=Sum("purchased_seats"))["total"] or 0
        used_seats = SoftwareLicense.objects.filter(deleted=False).aggregate(
            total=Sum("seats_used"))["total"] or 0

        total_cost = SoftwareLicense.objects.filter(
            deleted=False, cost__isnull=False
        ).aggregate(total=Sum("cost"))["total"] or 0

        by_type = dict(
            SoftwareLicense.objects.filter(deleted=False).values_list("license_type")
            .annotate(c=Count("id")).values_list("license_type", "c")
        )

        by_status = dict(
            SoftwareLicense.objects.filter(deleted=False).values_list("status")
            .annotate(c=Count("id")).values_list("status", "c")
        )

        compliance_count = ComplianceRecord.objects.filter(status="active").count()

        recent = SoftwareLicenseListSerializer(
            SoftwareLicense.objects.filter(deleted=False).order_by("-created_at")[:10], many=True
        ).data

        recent_alerts = MaintenanceAlertSerializer(
            MaintenanceAlert.objects.filter(
                category__in=("license_expiration", "license_seat_exhaustion")
            ).order_by("-created_at")[:10], many=True
        ).data

        return Response({
            "total_licenses": total_licenses,
            "active_licenses": active_licenses,
            "expired_licenses": expired_licenses,
            "expiring_soon": expiring_soon,
            "total_seats": total_seats,
            "used_seats": used_seats,
            "seat_utilization": round((used_seats / total_seats * 100), 1) if total_seats else 0,
            "total_license_cost": float(total_cost),
            "by_type": by_type,
            "by_status": by_status,
            "compliance_issues": compliance_count,
            "recent_licenses": recent,
            "recent_alerts": recent_alerts,
        })


@method_decorator(csrf_exempt, name="dispatch")
class LicenseUtilizationView(APIView):
    def get(self, request):
        licenses = SoftwareLicense.objects.filter(
            deleted=False, purchased_seats__gt=0
        ).select_related("department").order_by("-seats_used")

        result = []
        for lic in licenses:
            result.append({
                "license_id": lic.license_id,
                "software_name": lic.software_name,
                "license_type": lic.license_type,
                "purchased_seats": lic.purchased_seats,
                "seats_used": lic.seats_used,
                "seats_available": lic.seats_available,
                "utilization_pct": lic.utilization_pct,
                "department": lic.department.name if lic.department else "",
            })

        return Response(result)


@method_decorator(csrf_exempt, name="dispatch")
class LicenseCostAnalysisView(APIView):
    def get(self, request):
        total_cost = SoftwareLicense.objects.filter(
            deleted=False, cost__isnull=False
        ).aggregate(total=Sum("cost"))["total"] or 0

        by_type = []
        for item in SoftwareLicense.objects.filter(
            deleted=False, cost__isnull=False
        ).values("license_type").annotate(
            total=Sum("cost"), count=Count("id")
        ):
            by_type.append({
                "type": item["license_type"],
                "total_cost": float(item["total"]),
                "count": item["count"],
                "avg_cost": float(item["total"] / item["count"]) if item["count"] else 0,
            })

        by_department = []
        for item in SoftwareLicense.objects.filter(
            deleted=False, cost__isnull=False
        ).exclude(department__isnull=True).values(
            name=models.F("department__name")
        ).annotate(total=Sum("cost"), count=Count("id")):
            by_department.append({
                "department": item["name"],
                "total_cost": float(item["total"]),
                "count": item["count"],
            })

        expiring_cost = SoftwareLicense.objects.filter(
            deleted=False,
            expiration_date__lte=tz.now().date() + timedelta(days=90),
            expiration_date__gte=tz.now().date(),
            cost__isnull=False,
        ).aggregate(total=Sum("cost"))["total"] or 0

        return Response({
            "total_cost": float(total_cost),
            "by_type": by_type,
            "by_department": by_department,
            "renewal_cost_90_days": float(expiring_cost),
        })


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT VIEWS
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class MaintenanceExportView(APIView):
    def get(self, request):
        import csv
        from django.http import HttpResponse

        fmt = request.query_params.get("format", "csv")
        qs = MaintenanceRecord.objects.filter(deleted=False).select_related("asset", "department")

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(maintenance_id__icontains=search) |
                Q(asset__asset_name__icontains=search) |
                Q(vendor_name__icontains=search)
            )

        if fmt == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="maintenance_records.csv"'
            writer = csv.writer(response)
            writer.writerow([
                "Maintenance ID", "Asset Name", "Asset Tag", "Type", "Status",
                "Priority", "Scheduled Date", "Completion Date", "Vendor",
                "Technician", "Estimated Cost", "Actual Cost", "Downtime Hours",
            ])
            for m in qs:
                writer.writerow([
                    m.maintenance_id, m.asset.asset_name, m.asset.asset_tag,
                    m.maintenance_type, m.status, m.priority,
                    m.scheduled_date or "", m.completion_date or "",
                    m.vendor_name, m.technician,
                    m.estimated_cost or "", m.actual_cost or "",
                    m.downtime_hours,
                ])
            return response

        return Response(MaintenanceRecordListSerializer(qs, many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class LicenseExportView(APIView):
    def get(self, request):
        import csv
        from django.http import HttpResponse

        fmt = request.query_params.get("format", "csv")
        qs = SoftwareLicense.objects.filter(deleted=False).select_related("department")

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(license_id__icontains=search) |
                Q(software_name__icontains=search) |
                Q(vendor__icontains=search)
            )

        if fmt == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="software_licenses.csv"'
            writer = csv.writer(response)
            writer.writerow([
                "License ID", "Software Name", "Vendor", "Version", "Type",
                "License Key (Masked)", "Purchased Seats", "Seats Used",
                "Purchase Date", "Expiration Date", "Cost", "Status", "Department",
            ])
            for lic in qs:
                writer.writerow([
                    lic.license_id, lic.software_name, lic.vendor, lic.version,
                    lic.license_type, lic.license_key_masked,
                    lic.purchased_seats, lic.seats_used,
                    lic.purchase_date or "", lic.expiration_date or "",
                    lic.cost or "", lic.status,
                    lic.department.name if lic.department else "",
                ])
            return response

        return Response(SoftwareLicenseListSerializer(qs, many=True).data)


# ═══════════════════════════════════════════════════════════════════════════════
# ALERT CHECK TRIGGER VIEW
# ═══════════════════════════════════════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class AlertCheckView(APIView):
    def post(self, request):
        count = check_and_generate_alerts()
        return Response({"status": "ok", "alerts_created": count})
