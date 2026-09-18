"""气象日志接口：实际天气登记/导入，供养护记录天气核对。"""

from flask import Blueprint, request

from ..schemas import validate_weather_diary
from ..schemas.filters import weather_diary_filters
from ..services import WeatherDiaryService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("weather_diaries", __name__)


@bp.get("/weather-diaries")
def list_diaries():
    filters = weather_diary_filters(request.args)
    page, page_size = parse_page_args()
    query = WeatherDiaryService.list_diaries(filters, request.args)
    return ok(paginate(query, page, page_size))


@bp.get("/weather-diaries/districts")
def diary_districts():
    """已登记气象日志的行政区及日志条数，供筛选下拉使用。"""

    from sqlalchemy import func

    from ..extensions import db
    from ..models import WeatherDiary

    rows = (
        db.session.query(
            WeatherDiary.district, func.count(WeatherDiary.id)
        )
        .group_by(WeatherDiary.district)
        .order_by(WeatherDiary.district.asc())
        .all()
    )
    return ok([{"district": district, "count": count} for district, count in rows])


@bp.post("/weather-diaries")
def create_diary():
    payload = validate_weather_diary(json_body())
    diary = WeatherDiaryService.create(payload)
    return created(diary.to_dict(detail=True), message="气象日志已登记")


@bp.get("/weather-diaries/<int:diary_id>")
def get_diary(diary_id):
    return ok(WeatherDiaryService.get(diary_id).to_dict(detail=True))


@bp.put("/weather-diaries/<int:diary_id>")
def update_diary(diary_id):
    payload = validate_weather_diary(json_body())
    diary = WeatherDiaryService.update(diary_id, payload)
    return ok(diary.to_dict(detail=True), message="气象日志已更新")


@bp.delete("/weather-diaries/<int:diary_id>")
def delete_diary(diary_id):
    WeatherDiaryService.delete(diary_id)
    return ok(None, message="气象日志已删除")


@bp.post("/weather-diaries/import")
def import_diaries():
    body = json_body()
    entries = body.get("items") if isinstance(body, dict) else None
    result = WeatherDiaryService.import_entries(entries)
    message = (
        f"气象日志导入完成：新增 {result['created']} 条，更新 {result['updated']} 条"
    )
    if result["failed"]:
        message += f"，{len(result['failed'])} 条失败"
    return ok(result, message=message)
