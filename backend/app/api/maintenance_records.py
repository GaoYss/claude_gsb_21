"""养护记录接口。"""

from flask import Blueprint, request

from ..schemas import validate_maintenance_record, validate_weather_check
from ..schemas.filters import record_filters
from ..services import MaintenanceRecordService, WeatherDiaryService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("maintenance_records", __name__)


@bp.get("/maintenance-records/weather-check")
def record_weather_check():
    """表单实时核对：返回当日实际天气、建议天气与浇灌降雨提示。"""

    args = request.args
    payload = validate_weather_check({
        "green_space_id": args.get("green_space_id"),
        "task_id": args.get("task_id"),
        "record_date": args.get("record_date"),
        "weather": args.get("weather") or None,
        "work_content": args.get("work_content") or None,
    })
    check = WeatherDiaryService.cross_check(
        payload.get("green_space_id"),
        payload["record_date"],
        weather=payload.get("weather"),
        task_id=payload.get("task_id"),
        work_content=payload.get("work_content"),
    )
    return ok(check)


@bp.get("/maintenance-records")
def list_records():
    filters = record_filters(request.args)
    page, page_size = parse_page_args()
    query = MaintenanceRecordService.list_records(filters, request.args)
    data = paginate(query, page, page_size)
    data["summary"] = MaintenanceRecordService.summary(filters)
    return ok(data)


@bp.get("/maintenance-records/summary")
def records_summary():
    return ok(MaintenanceRecordService.summary(record_filters(request.args)))


@bp.post("/maintenance-records")
def create_record():
    payload = validate_maintenance_record(json_body())
    record = MaintenanceRecordService.create(payload)
    return created(record.to_dict(detail=True), message="养护记录录入成功")


@bp.get("/maintenance-records/<int:record_id>")
def get_record(record_id):
    return ok(MaintenanceRecordService.detail(record_id))


@bp.put("/maintenance-records/<int:record_id>")
def update_record(record_id):
    payload = validate_maintenance_record(json_body())
    record = MaintenanceRecordService.update(record_id, payload)
    return ok(record.to_dict(detail=True), message="养护记录已更新")


@bp.delete("/maintenance-records/<int:record_id>")
def delete_record(record_id):
    MaintenanceRecordService.delete(record_id)
    return ok(None, message="养护记录已删除")
