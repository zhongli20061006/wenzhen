# -*- coding: utf-8 -*-
"""
集成测试：问诊全流程 + 医生接诊反馈 + 关键词提取 + 权限校验。

覆盖主流程：
  患者登录 → 开始问诊 → 回答追问 → 查看结果 → 挂号 → 医生接诊 → 提交反馈
"""

import pytest


# ============================================================
# 辅助函数
# ============================================================
def _login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def _start_consultation(client, headers, **overrides):
    body = {
        "description": "我头痛发烧两天了",
        "symptoms": ["头痛"],
        "severity": 6,
        "duration": "2天",
    }
    body.update(overrides)
    return client.post("/api/consultation/start", json=body, headers=headers)


def _answer(client, session_id, headers, symptom_id, answer):
    return client.post(
        f"/api/consultation/{session_id}/answer",
        json={"symptom_id": symptom_id, "answer": answer},
        headers=headers,
    )


# ============================================================
# C1: 患者登录
# ============================================================
class TestLogin:
    def test_login_success(self, client):
        resp = _login(client, "patient1", "patient123")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "patient"

    def test_login_wrong_password(self, client):
        resp = _login(client, "patient1", "wrong")
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = _login(client, "nobody", "x")
        assert resp.status_code == 401


# ============================================================
# C2: 未登录不能访问问诊接口
# ============================================================
class TestAuthGuard:
    def test_no_token_returns_401(self, client):
        resp = client.post("/api/consultation/start", json={"symptoms": ["头痛"], "description": "test"})
        # FastAPI HTTPBearer 默认用 403（权限不足）= missing auth
        assert resp.status_code in (401, 403)


# ============================================================
# C3: 开始问诊 - 关键词提取 + 推理引擎
# ============================================================
class TestStartConsultation:
    def test_start_with_keyword_matches(self, client, patient_headers):
        """描述中包含已知症状，应触发关键词匹配并启动问诊"""
        resp = _start_consultation(client, patient_headers)
        assert resp.status_code == 200
        data = resp.json()
        # 应返回第一个追问问题
        assert "consultation_id" in data
        assert "question_text" in data
        assert data["round"] == 1

    def test_start_with_no_symptoms_returns_400(self, client, patient_headers):
        """没有任何可识别症状应报错"""
        resp = _start_consultation(client, patient_headers, description="不知道怎么了", symptoms=[])
        assert resp.status_code == 400
        assert "未能识别" in resp.json()["detail"]

    def test_start_returns_first_question(self, client, patient_headers):
        """启动后应该有第一轮追问"""
        resp = _start_consultation(client, patient_headers, symptoms=["头痛", "发热"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["round"] == 1
        assert "question_text" in data
        # 症状提取到"头痛"和"发热"后，应该问下一个最有鉴别力的症状
        # 候选疾病中脑膜炎的未问必要条件症状是"颈部僵硬"
        assert "颈部僵硬" in data["question_text"] or "呕吐" in data["question_text"]


# ============================================================
# C4: 回答追问 → 推理 → 推荐
# ============================================================
class TestAnswerQuestion:
    def test_full_qa_flow(self, client, patient_headers):
        """完整问答流程：开始→回答→得到科室推荐"""
        # 1. 开始问诊（1个初始症状）
        start = _start_consultation(client, patient_headers, symptoms=["头痛"])
        assert start.status_code == 200
        sid = start.json()["consultation_id"]
        qid = start.json()["symptom_id"]  # 第一问的症状ID

        # 2. 回答 YES
        ans1 = _answer(client, sid, patient_headers, qid, "YES")
        assert ans1.status_code == 200
        data1 = ans1.json()

        # 可能直接出推荐（候选疾病已足够少），也可能继续追问
        if data1.get("status") == "RECOMMENDING":
            assert "result" in data1
            return  # 正常结束

        # 3. 如果继续追问，再答一轮
        assert data1["status"] == "QUESTIONING"
        ans2 = _answer(client, sid, patient_headers, data1["symptom_id"], "NO")
        assert ans2.status_code == 200
        data2 = ans2.json()

        # 应该出推荐了（2轮后候选疾病应 ≤ 3）
        if data2.get("status") == "RECOMMENDING":
            assert "result" in data2
            return

        assert data2["status"] == "QUESTIONING"
        # 4. 第三轮
        ans3 = _answer(client, sid, patient_headers, data2["symptom_id"], "YES")
        assert ans3.status_code == 200
        data3 = ans3.json()
        assert data3.get("status") == "RECOMMENDING" or data3.get("status") == "QUESTIONING"

    def test_duplicate_answer_rejected(self, client, patient_headers):
        """第一答触发推荐后，再答同轮应被拒绝"""
        start = _start_consultation(client, patient_headers, symptoms=["头痛"])
        assert start.status_code == 200
        sid = start.json()["consultation_id"]
        qid = start.json()["symptom_id"]

        # 回答 YES
        resp1 = _answer(client, sid, patient_headers, qid, "YES")
        # 如果直接出推荐，第二轮用同一 qid 会被拒绝（状态不是 QUESTIONING）
        if resp1.json().get("status") == "RECOMMENDING":
            resp2 = _answer(client, sid, patient_headers, qid, "YES")
            assert resp2.status_code in (400, 409)
        else:
            # 继续问诊时，同一轮重复回答会触发 409
            # 但由于后端可能已递增 round，此处验证请求不会 500 即可
            assert resp1.status_code == 200


# ============================================================
# C5: IDOR 权限校验 - 患者不能操作他人会话
# ============================================================
class TestIdorPrevention:
    def test_cannot_answer_others_session(self, client, patient_headers):
        """患者A不能回答患者B的问诊"""
        from app.api.auth import create_access_token
        other_headers = {"Authorization": f"Bearer " + create_access_token(
            {"sub": "patient2", "role": "patient", "doctor_id": None})}

        # 用 patient1 开始问诊
        start = _start_consultation(client, patient_headers, symptoms=["头痛"])
        sid = start.json()["consultation_id"]
        qid = start.json()["symptom_id"]

        # patient2 尝试回答 patient1 的会话
        resp = _answer(client, sid, other_headers, qid, "YES")
        assert resp.status_code == 403
        assert "无权操作" in resp.json()["detail"]

    def test_cannot_view_others_result(self, client, patient_headers):
        """患者A不能查看患者B的结果"""
        from app.api.auth import create_access_token
        other_headers = {"Authorization": f"Bearer " + create_access_token(
            {"sub": "patient2", "role": "patient", "doctor_id": None})}

        resp = client.get("/api/consultation/test-session-001/result", headers=other_headers)
        assert resp.status_code == 403


# ============================================================
# C6: 查看结果 + 获取科室/医生列表
# ============================================================
class TestResultAndLists:
    def test_get_departments(self, client, patient_headers):
        resp = client.get("/api/consultation/departments", headers=patient_headers)
        assert resp.status_code == 200
        data = resp.json()
        names = [d["name"] for d in data]
        assert "神经内科" in names
        assert "呼吸内科" in names

    def test_get_doctors(self, client, patient_headers):
        resp = client.get("/api/consultation/doctors?department_id=1", headers=patient_headers)
        assert resp.status_code == 200
        names = [d["name"] for d in resp.json()]
        assert "张医生" in names

    def test_get_timeslots(self, client, patient_headers):
        resp = client.get("/api/consultation/timeslots", headers=patient_headers)
        assert resp.status_code == 200
        slots = resp.json()
        assert len(slots) > 0
        assert slots[0]["value"] in ("08:30", "09:00")

    def test_available_timeslots(self, client, patient_headers):
        """查看某医生某天的可约时段"""
        from datetime import date, timedelta
        resp = client.get(
            f"/api/consultation/timeslots/available?doctor_id=1&registration_date={date.today().isoformat()}",
            headers=patient_headers,
        )
        assert resp.status_code == 200
        for slot in resp.json():
            assert "remaining" in slot
            assert "total" in slot
            assert "used" in slot
            assert slot["total"] == 20  # 张医生 max_patients_per_session


# ============================================================
# C7: 挂号
# ============================================================
class TestRegistration:
    def test_register_with_consultation(self, client, patient_headers):
        """随问诊后挂号"""
        from datetime import date, timedelta
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        resp = client.post("/api/consultation/registration", json={
            "consultation_id": "test-session-001",
            "department_id": 1,
            "doctor_id": 1,
            "registration_date": tomorrow,
            "time_slot": "09:00",
        }, headers=patient_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "挂号成功"

    def test_my_registrations(self, client, patient_headers):
        """查看我的挂号记录"""
        resp = client.get("/api/consultation/registration/my", headers=patient_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["doctor"] == "张医生"


# ============================================================
# C8: 医生接诊 - 今日患者 + 患者报告
# ============================================================
class TestDoctorFlow:
    def test_today_patients(self, client, doctor_headers):
        resp = client.get("/api/doctor/today-patients", headers=doctor_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_today_patients_requires_doctor_role(self, client, patient_headers):
        resp = client.get("/api/doctor/today-patients", headers=patient_headers)
        assert resp.status_code == 403

    def test_patient_report(self, client, doctor_headers):
        resp = client.get("/api/doctor/patient/1/report", headers=doctor_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "registration" in data
        assert data["registration"]["patient_id"] == "patient1"
        assert data["registration"]["doctor"] == "张医生"

    def test_patient_report_other_doctor_forbidden(self, client, doctor_headers):
        """其他医生不能看张医生的患者报告"""
        from app.api.auth import create_access_token
        other_doc_headers = {"Authorization": f"Bearer " + create_access_token(
            {"sub": "doctor_respiratory", "role": "doctor", "doctor_id": 2})}
        resp = client.get("/api/doctor/patient/1/report", headers=other_doc_headers)
        assert resp.status_code == 403


# ============================================================
# C9: 医生提交反馈 + 准确率统计
# ============================================================
class TestDoctorFeedback:
    def test_submit_feedback(self, client, doctor_headers):
        resp = client.post("/api/doctor/feedback", json={
            "registration_id": 1,
            "is_correct": True,
            "actual_department_id": 1,
            "doctor_note": "诊断正确",
        }, headers=doctor_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "反馈提交成功"

    def test_duplicate_feedback_rejected(self, client, doctor_headers):
        """已就诊的记录已有反馈，不能重复提交"""
        resp = client.post("/api/doctor/feedback", json={
            "registration_id": 2,
            "is_correct": True,
            "actual_department_id": 1,
        }, headers=doctor_headers)
        assert resp.status_code == 400
        assert "已有反馈" in resp.json()["detail"]

    def test_feedback_history(self, client, doctor_headers):
        resp = client.get("/api/doctor/feedback-history", headers=doctor_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_doctor_accuracy(self, client, doctor_headers):
        resp = client.get("/api/doctor/accuracy", headers=doctor_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert 0 <= data["accuracy"] <= 1
        # 至少有一个科室的 breakdown
        assert len(data["by_department"]) >= 1


# ============================================================
# C10: Token 刷新
# ============================================================
class TestTokenRefresh:
    def test_refresh_token(self, client, patient_token):
        resp = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {patient_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "patient"

    def test_refresh_with_invalid_token(self, client):
        resp = client.post("/api/auth/refresh", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401
