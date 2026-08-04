# -*- coding: utf-8 -*-
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine  # noqa: E402


class TikuTemplateTest(unittest.TestCase):
    def test_eleven_templates_with_required_fields(self):
        self.assertEqual(len(engine.TIKU_TEMPLATES), 11)
        for t in engine.TIKU_TEMPLATES:
            for key in ("articleId", "title", "question", "quesType"):
                self.assertIn(key, t, "模板缺少字段 %s" % key)
                self.assertTrue(str(t[key]), "模板字段 %s 为空" % key)
        titles = [t["title"] for t in engine.TIKU_TEMPLATES]
        self.assertEqual(len(set(titles)), 11, "课程标题不应重复")


class RunByUseridValidationTest(unittest.TestCase):
    def test_invalid_userid_raises(self):
        for bad in ("abc", "12.5", "", "19位数字带空格-x", "  "):
            with self.assertRaises(engine.EngineError, msg="应拒绝非法输入: %r" % bad):
                engine.run_by_userid(bad)

    def test_valid_userid_passes_validation(self):
        # 校验通过后会进入网络请求，这里 mock 掉网络部分
        with mock.patch.object(engine, "_run_flow", return_value={"score": 100, "elapsed_ms": 1.0}) as m:
            result = engine.run_by_userid("1234567890123456789")
            m.assert_called_once()
            self.assertEqual(result, {"score": 100, "elapsed_ms": 1.0})


class QuerySchoolsTest(unittest.TestCase):
    SAMPLE = {
        "data": [
            {"id": "1224316234189443001", "name": "南京晓庄学院"},
            {"id": "1224316234189443002", "name": "南京大学"},
            {"id": "1224316234189443003", "name": "东南大学"},
        ]
    }

    def test_filter_by_keyword(self):
        with mock.patch.object(engine.utils, "getAllSchools", return_value=json.dumps(self.SAMPLE)):
            schools = engine.query_schools("南京")
            self.assertEqual(len(schools), 2)
            self.assertEqual(schools[0]["name"], "南京晓庄学院")
            self.assertEqual(schools[0]["id"], "1224316234189443001")

    def test_no_match_returns_empty(self):
        with mock.patch.object(engine.utils, "getAllSchools", return_value=json.dumps(self.SAMPLE)):
            self.assertEqual(engine.query_schools("不存在的学校"), [])

    def test_network_error_propagates(self):
        with mock.patch.object(engine.utils, "getAllSchools", side_effect=Exception("网络异常")):
            with self.assertRaises(Exception):
                engine.query_schools("南京")


class LoginTest(unittest.TestCase):
    def test_login_failure_raises(self):
        with mock.patch.object(engine.utils, "loginMethod",
                               return_value={"success": False, "message": "密码错误"}):
            with self.assertRaises(engine.EngineError):
                engine.login_and_get_user("1224", "u", "p")

    def test_login_success_returns_user_id(self):
        fake = {"success": True, "data": {"userId": "1951234567890123456"}}
        with mock.patch.object(engine.utils, "loginMethod", return_value=fake):
            uid, data = engine.login_and_get_user("1224", "u", "p")
            self.assertEqual(uid, "1951234567890123456")


class MaskUserIdTest(unittest.TestCase):
    def test_mask_long_userid(self):
        self.assertEqual(engine._mask_userid("1951234567890123456"), "195***456")

    def test_mask_short_userid(self):
        self.assertEqual(engine._mask_userid("12345"), "12***5")

    def test_mask_empty(self):
        # 空字符串仅做展示用途，不应抛异常
        self.assertEqual(engine._mask_userid(""), "***")


if __name__ == "__main__":
    unittest.main()
