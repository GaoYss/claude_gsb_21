"""气象日志与养护记录天气核对测试。"""

from datetime import date


# ---------------------------------------------------------------- 气象日志维护
def test_create_weather_diary(api, make_space):
    make_space(district="西湖区")
    data = api.data(api.post("/api/v1/weather-diaries", {
        "district": "西湖区",
        "diary_date": "2026-06-10",
        "weather": "rain",
        "rainfall_mm": 12.5,
        "source": "imported",
    }), 201)
    assert data["district"] == "西湖区"
    assert data["weather"] == "rain"
    assert data["weather_label"] == "雨"
    assert data["rainfall_mm"] == 12.5
    assert data["is_rainy"] is True
    assert data["source_label"] == "气象台导入"


def test_duplicate_district_date_diary_rejected(api, make_diary):
    diary = make_diary()
    response = api.post("/api/v1/weather-diaries", {
        "district": diary.district,
        "diary_date": "2026-06-10",
        "weather": "sunny",
    })
    assert response.status_code == 409
    assert "已存在" in response.get_json()["message"]


def test_diary_requires_fields(api):
    response = api.post("/api/v1/weather-diaries", {"district": "西湖区"})
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert "diary_date" in details
    assert "weather" in details


def test_update_and_delete_diary(api, make_diary):
    diary = make_diary(weather="sunny")
    updated = api.data(api.put(f"/api/v1/weather-diaries/{diary.id}", {
        "district": diary.district,
        "diary_date": "2026-06-10",
        "weather": "cloudy",
    }))
    assert updated["weather"] == "cloudy"

    api.delete(f"/api/v1/weather-diaries/{diary.id}")
    listing = api.data(api.get("/api/v1/weather-diaries", district=diary.district))
    assert listing["meta"]["total"] == 0


def test_list_diaries_with_filters(api, make_diary):
    make_diary(district="西湖区", day=date(2026, 6, 10), weather="rain", rainfall_mm=8)
    make_diary(district="拱墅区", day=date(2026, 6, 11), weather="sunny")

    rainy = api.data(api.get("/api/v1/weather-diaries", rainy="true"))
    assert rainy["meta"]["total"] == 1
    assert rainy["items"][0]["weather"] == "rain"

    by_district = api.data(api.get("/api/v1/weather-diaries", district="拱墅区"))
    assert by_district["meta"]["total"] == 1

    ranged = api.data(api.get("/api/v1/weather-diaries", date_from="2026-06-11",
                              date_to="2026-06-30"))
    assert ranged["meta"]["total"] == 1


def test_diary_import_upserts_and_reports_failures(api, make_diary):
    make_diary(district="西湖区", day=date(2026, 6, 10), weather="sunny")
    result = api.data(api.post("/api/v1/weather-diaries/import", {"items": [
        {"district": "西湖区", "diary_date": "2026-06-10", "weather": "rain", "rainfall_mm": 6},
        {"district": "滨江区", "diary_date": "2026-06-11", "weather": "cloudy"},
        {"district": "上城区", "diary_date": "bad-date", "weather": "sunny"},
    ]}))
    assert result["created"] == 1
    assert result["updated"] == 1
    assert len(result["failed"]) == 1
    assert result["failed"][0]["index"] == 2

    updated = api.data(api.get("/api/v1/weather-diaries", district="西湖区"))
    assert updated["items"][0]["weather"] == "rain"


# ---------------------------------------------------------------- 天气核对
def test_record_weather_consistent_with_diary(api, make_space, make_diary):
    space = make_space(district="西湖区")
    make_diary(district="西湖区", day=date(2026, 6, 10), weather="sunny")
    record = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "record_date": "2026-06-10",
        "work_content": "修剪绿篱",
        "weather": "sunny",
    }), 201)
    assert record["weather_match"] == "consistent"
    assert record["weather_conflict"] is False


def test_record_weather_mismatch_is_kept_and_marked(api, make_space, make_diary):
    space = make_space(district="西湖区")
    make_diary(district="西湖区", day=date(2026, 6, 10), weather="rain", rainfall_mm=15)
    # 冲突不阻断保存，仍返回 201
    record = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "record_date": "2026-06-10",
        "work_content": "修剪绿篱",
        "weather": "sunny",
    }), 201)
    assert record["weather_match"] == "mismatch"
    assert record["weather_conflict"] is True
    note = record["weather_conflict_note"]
    assert "不一致" in note and "按填报内容留存" in note

    detail = api.data(api.get(f"/api/v1/maintenance-records/{record['id']}"))
    assert detail["weather_conflict_note"] == note
    assert detail["weather_checked_at"]


def test_record_without_diary_marked_unavailable(api, make_space):
    space = make_space(district="西湖区")
    record = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "record_date": "2026-06-10",
        "work_content": "修剪绿篱",
        "weather": "sunny",
    }), 201)
    assert record["weather_match"] == "unavailable"
    assert record["weather_conflict_note"] is None


def test_blank_weather_auto_filled_from_diary(api, make_space, make_diary):
    space = make_space(district="西湖区")
    make_diary(district="西湖区", day=date(2026, 6, 10), weather="cloudy")
    record = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "record_date": "2026-06-10",
        "work_content": "修剪绿篱",
    }), 201)
    assert record["weather"] == "cloudy"
    assert record["weather_match"] == "consistent"


def test_weather_check_preview(api, make_space, make_diary):
    space = make_space(district="西湖区")
    make_diary(district="西湖区", day=date(2026, 6, 10), weather="rain", rainfall_mm=9)
    data = api.data(api.get("/api/v1/maintenance-records/weather-check",
                            green_space_id=space.id, record_date="2026-06-10",
                            weather="sunny", work_content="修剪绿篱"))
    assert data["actual_weather"] == "rain"
    assert data["suggested_weather"] == "rain"
    assert data["weather_match"] == "mismatch"


# ---------------------------------------------------------------- 浇灌提示
def test_watering_on_rainy_day_warns(api, make_space, make_diary):
    space = make_space(district="西湖区")
    make_diary(district="西湖区", day=date(2026, 6, 10), weather="rain", rainfall_mm=20)
    record = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "record_date": "2026-06-10",
        "work_content": "对花境与草坪浇灌 4 车次",
        "weather": "rain",
    }), 201)
    assert record["weather_match"] == "consistent"
    assert "降雨" in record["weather_conflict_note"]
    assert "保留登记" in record["weather_conflict_note"]


def test_watering_task_type_triggers_warning(api, make_task, make_diary):
    task = make_task(task_type="water", plan_date=date(2026, 6, 11))
    make_diary(district=task.green_space.district, day=date(2026, 6, 11), weather="rain")
    record = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": task.id,
        "record_date": "2026-06-11",
        "work_content": "早晚两班次浇灌新栽苗木 260 株",
    }), 201)
    assert "降雨" in record["weather_conflict_note"]


def test_warning_within_two_days_after_rain(api, make_space, make_diary):
    space = make_space(district="西湖区")
    make_diary(district="西湖区", day=date(2026, 6, 10), weather="rain", rainfall_mm=30)

    warning = api.data(api.get("/api/v1/maintenance-records/weather-check",
                               green_space_id=space.id, record_date="2026-06-12",
                               work_content="浇灌草坪"))
    assert len(warning["warnings"]) == 1

    outside = api.data(api.get("/api/v1/maintenance-records/weather-check",
                               green_space_id=space.id, record_date="2026-06-13",
                               work_content="浇灌草坪"))
    assert outside["warnings"] == []


def test_drainage_work_on_rainy_day_is_not_warned(api, make_space, make_diary):
    space = make_space(district="西湖区")
    make_diary(district="西湖区", day=date(2026, 6, 10), weather="rain", rainfall_mm=20)
    record = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "record_date": "2026-06-10",
        "work_content": "雨后对积水树穴开沟排涝排水",
        "weather": "rain",
    }), 201)
    assert record["weather_match"] == "consistent"
    assert record["weather_conflict_note"] is None


def test_watering_keyword_in_plain_record_warns(api, make_space, make_diary):
    space = make_space(district="西湖区")
    make_diary(district="西湖区", day=date(2026, 6, 10), weather="rain")
    data = api.data(api.get("/api/v1/maintenance-records/weather-check",
                            green_space_id=space.id, record_date="2026-06-10",
                            work_content="日常巡查并顺带浇水"))
    assert len(data["warnings"]) == 1


# ---------------------------------------------------------------- 日志变动后回查
def test_adding_diary_retroactively_checks_existing_record(api, make_record):
    record = make_record(record_date=date(2026, 6, 10), weather="sunny", work_content="修剪绿篱")
    assert record.weather_match == "unavailable"

    api.post("/api/v1/weather-diaries", {
        "district": record.green_space.district,
        "diary_date": "2026-06-10",
        "weather": "sunny",
    })
    detail = api.data(api.get(f"/api/v1/maintenance-records/{record.id}"))
    assert detail["weather_match"] == "consistent"


def test_deleting_rainy_diary_clears_watering_warning(api, make_space, make_diary):
    space = make_space(district="西湖区")
    diary = make_diary(district="西湖区", day=date(2026, 6, 10), weather="rain", rainfall_mm=20)
    record = api.data(api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "record_date": "2026-06-10",
        "work_content": "浇灌花境",
        "weather": "rain",
    }), 201)
    assert record["weather_conflict_note"]

    api.delete(f"/api/v1/weather-diaries/{diary.id}")
    detail = api.data(api.get(f"/api/v1/maintenance-records/{record['id']}"))
    assert detail["weather_match"] == "unavailable"
    assert detail["weather_conflict_note"] is None


def test_conflict_filter_in_list(api, make_space, make_diary):
    space = make_space(district="西湖区")
    make_diary(district="西湖区", day=date(2026, 6, 10), weather="rain")
    api.post("/api/v1/weather-diaries", {
        "district": "西湖区", "diary_date": "2026-06-11", "weather": "sunny",
    })
    api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id, "record_date": "2026-06-10",
        "work_content": "修剪", "weather": "sunny",
    })
    api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id, "record_date": "2026-06-11",
        "work_content": "修剪", "weather": "sunny",
    })

    conflicts = api.data(api.get("/api/v1/maintenance-records", weather_conflict="true"))
    assert conflicts["meta"]["total"] == 1
    mismatches = api.data(api.get("/api/v1/maintenance-records", weather_match="mismatch"))
    assert mismatches["meta"]["total"] == 1
    assert conflicts["summary"]["weather_conflict_count"] == 1


def test_green_space_profile_reports_conflict_count(api, make_space, make_diary):
    space = make_space(district="西湖区")
    make_diary(district="西湖区", day=date(2026, 6, 10), weather="rain")
    api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "record_date": "2026-06-10",
        "work_content": "浇灌花境",
        "weather": "sunny",
    })
    profile = api.data(api.get(f"/api/v1/green-spaces/{space.id}/profile"))
    assert profile["statistics"]["weather_conflict_count"] == 1
    recent = profile["recent_records"][0]
    assert recent["weather_match"] == "mismatch"
    assert recent["weather_conflict_note"]


def test_check_preview_requires_space_or_task(api):
    response = api.get("/api/v1/maintenance-records/weather-check", record_date="2026-06-10")
    assert response.status_code == 422


def test_check_preview_derives_space_from_task(api, make_task, make_diary):
    task = make_task()
    make_diary(district=task.green_space.district, day=date(2026, 3, 10), weather="overcast")
    data = api.data(api.get("/api/v1/maintenance-records/weather-check",
                            task_id=task.id, record_date="2026-03-10", weather="overcast"))
    assert data["district"] == task.green_space.district
    assert data["weather_match"] == "consistent"


def test_overview_and_reminders_include_weather_conflicts(api, make_space, make_diary):
    space = make_space(district="西湖区")
    make_diary(district="西湖区", day=date(2026, 6, 10), weather="rain")
    api.post("/api/v1/maintenance-records", {
        "green_space_id": space.id,
        "record_date": "2026-06-10",
        "work_content": "浇灌花境",
        "weather": "sunny",
    })

    overview = api.data(api.get("/api/v1/statistics/overview"))
    assert overview["record"]["weather_conflict_count"] == 1

    reminders = api.data(api.get("/api/v1/statistics/reminders"))
    assert len(reminders["weather_conflicts"]) == 1
    assert reminders["weather_conflicts"][0]["weather_conflict_note"]

    dashboard = api.data(api.get("/api/v1/statistics/dashboard"))
    assert len(dashboard["weather_conflict_records"]) == 1
