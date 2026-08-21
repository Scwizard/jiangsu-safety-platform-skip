# -*- coding: utf-8 -*-
"""离线端到端流程测试：mock 全部网络请求，验证引擎接线逻辑。"""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine  # noqa: E402


def make_post_side_effect():
    """模拟 compulsory/list 两次返回（先未完成、后全部完成）+ unitTest 应答。"""
    calls = {"list": 0}

    def fake_post(url, data=None, **kwargs):
        if "compulsory/list" in url:
            calls["list"] += 1
            if calls["list"] == 1:
                course = [{"isFinsh": False, "name": "课程%d" % i} for i in range(11)]
            else:
                course = [{"isFinsh": True, "name": "课程%d" % i} for i in range(11)]
            return mock.Mock(text=json.dumps({"data": course}))
        if "unitTest" in url:
            return mock.Mock(text="{}")
        raise AssertionError("unexpected post url: %s" % url)

    return fake_post


class FullFlowTest(unittest.TestCase):
    def test_run_by_userid_full_flow(self):
        with mock.patch("requests.post", side_effect=make_post_side_effect()), \
             mock.patch.object(engine.utils, "creatExam", return_value={"data": {"logId": "123"}}), \
             mock.patch.object(engine.utils, "getExam",
                               return_value={"data": {"data": [{"questionId": str(i)} for i in range(50)]}}), \
             mock.patch.object(engine.utils, "getExamId", return_value={"code": 200, "data": {"id": "exam1"}}), \
             mock.patch.object(engine.utils, "getAnswerById",
                               return_value=(("question", "1-A"), ("questionId", "1"), ("quesType", "1"))), \
             mock.patch.object(engine.utils, "imitateExam",
                               return_value=mock.Mock(text=json.dumps({"data": {"count": 100}}))), \
             mock.patch.object(engine.utils, "upload_stats", return_value={"status": "ok"}):
            logs = []
            result = engine.run_by_userid("1234567890123456789", log=logs.append)
            self.assertEqual(result["score"], 100)
            self.assertGreater(result["elapsed_ms"], 0)
            joined = "\n".join(logs)
            self.assertIn("得分：100", joined)
            self.assertIn("证书", joined)
            self.assertIn("脚本统计执行成功", joined)

    def test_run_by_login_full_flow_and_untying(self):
        with mock.patch("requests.post", side_effect=make_post_side_effect()), \
             mock.patch.object(engine.utils, "loginMethod",
                               return_value={"success": True, "data": {"userId": "1951234567890123456"}}), \
             mock.patch.object(engine.utils, "creatExam", return_value={"data": {"logId": "123"}}), \
             mock.patch.object(engine.utils, "getExam",
                               return_value={"data": {"data": [{"questionId": str(i)} for i in range(50)]}}), \
             mock.patch.object(engine.utils, "getExamId", return_value={"code": 200, "data": {"id": "exam1"}}), \
             mock.patch.object(engine.utils, "getAnswerById",
                               return_value=(("question", "1-A"), ("questionId", "1"), ("quesType", "1"))), \
             mock.patch.object(engine.utils, "imitateExam",
                               return_value=mock.Mock(text=json.dumps({"data": {"count": 100}}))), \
             mock.patch.object(engine.utils, "upload_stats", return_value={"status": "ok"}), \
             mock.patch.object(engine.utils, "UntyingMethod", return_value={"success": True}):
            logs = []
            result = engine.run_by_login("1224", "user", "pass", log=logs.append)
            self.assertEqual(result["score"], 100)
            joined = "\n".join(logs)
            self.assertIn("获取到了userId", joined)
            self.assertIn("解绑openId", joined)

    def test_cancel_between_steps(self):
        """取消标志置位后，流程在步骤之间抛出 RunCancelled。"""
        calls = {"check": 0}

        def check_cancel():
            calls["check"] += 1
            if calls["check"] >= 2:
                raise engine.RunCancelled()

        with mock.patch("requests.post", side_effect=make_post_side_effect()):
            with self.assertRaises(engine.RunCancelled):
                engine.run_by_userid("1234567890123456789", check_cancel=check_cancel)
        # 第 1 次放行（发起了课程列表请求），第 2 次才取消，验证是“步骤之间”取消
        self.assertGreaterEqual(calls["check"], 2)


class RegressionTest(unittest.TestCase):
    """回归：缺答案错误透传 + 登录入口接受学校名称。"""

    def test_missing_answer_raises_engine_error_with_question_id(self):
        with mock.patch("requests.post", side_effect=make_post_side_effect()), \
             mock.patch.object(engine.utils, "creatExam", return_value={"data": {"logId": "123"}}), \
             mock.patch.object(engine.utils, "getExam",
                               return_value={"data": {"data": [{"questionId": "q1"}]}}), \
             mock.patch.object(engine.utils, "getExamId", return_value={"code": 200, "data": {"id": "exam1"}}), \
             mock.patch.object(engine.utils, "getAnswerById",
                               side_effect=LookupError("题库缺少题目 q1 的答案")):
            with self.assertRaises(engine.EngineError) as cm:
                engine.run_by_userid("1234567890123456789")
            self.assertIn("题库缺少题目 q1", str(cm.exception))

    def test_run_by_login_accepts_school_name(self):
        captured = {}

        def fake_login(username, password, college_id):
            captured["college_id"] = college_id
            return {"success": True, "data": {"userId": "1951234567890123456"}}

        with mock.patch.object(engine.utils, "getAllSchools",
                               return_value=json.dumps({"data": [{"id": "s1", "name": "测试大学"}]})), \
             mock.patch.object(engine.utils, "loginMethod", side_effect=fake_login), \
             mock.patch.object(engine, "_run_flow", return_value={"score": 100, "elapsed_ms": 1.0}):
            result = engine.run_by_login("测试大学", "user", "pass")
        self.assertEqual(captured["college_id"], "s1")
        self.assertEqual(result["score"], 100)


if __name__ == "__main__":
    unittest.main()
