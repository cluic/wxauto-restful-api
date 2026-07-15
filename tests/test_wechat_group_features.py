import asyncio
import inspect
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# Importing the production service normally initializes the Windows-only SDK.
# These small module stubs keep the tests isolated from WeChat and licensing
# while leaving the real WeChatService implementation under test.
_fake_init = types.ModuleType("app.services.init")
_fake_init.WeChat = type("WeChat", (), {})
_fake_init.Chat = type("Chat", (), {})
_fake_init.HumanMessage = type("HumanMessage", (), {})
_fake_init.WxClient = {}
_fake_init.safe_initialize_wechat = lambda: True
sys.modules.setdefault("app.services.init", _fake_init)

_fake_error_handler = types.ModuleType("app.utils.error_handler")


def _identity_error_handler(**_kwargs):
    def decorator(function):
        return function

    return decorator


_fake_error_handler.handle_service_error = _identity_error_handler
sys.modules.setdefault("app.utils.error_handler", _fake_error_handler)

from app.api.v1 import wechat as wechat_api
from app.services import wechat_service


class _ImmediateQueue:
    """Execute queued service work immediately, without a worker thread."""

    def __init__(self):
        self.submissions = []

    async def submit(
        self,
        operation,
        *args,
        priority=0,
        timeout=30.0,
        max_retries=3,
        **kwargs,
    ):
        self.submissions.append(
            {
                "priority": priority,
                "timeout": timeout,
                "max_retries": max_retries,
            }
        )
        return operation(*args, **kwargs)


class _SuccessfulWxResponse(dict):
    def __init__(self):
        super().__init__(message="操作成功", data=None)

    def __bool__(self):
        return True


class _FailedWxResponse(dict):
    def __init__(self):
        super().__init__(message="没有群管理权限", data={"reason": "forbidden"})

    def __bool__(self):
        return False


def _invoke(result):
    """Resolve either an async service result or a synchronous one."""

    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


class WeChatGroupServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = object.__new__(wechat_service.WeChatService)
        self.service._queue = _ImmediateQueue()

        self.wx = MagicMock(name="wx_sdk")
        successful = _SuccessfulWxResponse()
        self.wx.AddGroupMembers.return_value = successful
        self.wx.CreateGroup.return_value = successful
        self.wx.SetGroupName.return_value = successful
        self.wx.SetGroupRemark.return_value = successful
        self.wx.SetGroupAnnouncement.return_value = successful
        self.wx.SetGroupMyNickname.return_value = successful
        self.wx.ChatInfo.return_value = {
            "chat_name": "项目群",
            "chat_type": "group",
            "group_member_count": 3,
        }

        self.get_wechat = patch.object(
            wechat_service, "get_wechat", return_value=self.wx
        ).start()
        self.switch_chat = patch.object(
            wechat_service, "safe_switch_chat", return_value=True
        ).start()
        self.addCleanup(patch.stopall)

    def test_expected_public_method_signatures(self):
        expected = {
            "get_chat_info": ["self", "who", "exact", "wxname"],
            "add_group_members": ["self", "members", "who", "exact", "wxname"],
            "create_group": ["self", "contacts", "wxname"],
            "set_group_name": ["self", "value", "who", "exact", "wxname"],
            "set_group_remark": ["self", "value", "who", "exact", "wxname"],
            "set_group_announcement": [
                "self",
                "value",
                "who",
                "exact",
                "wxname",
            ],
            "set_group_my_nickname": [
                "self",
                "value",
                "who",
                "exact",
                "wxname",
            ],
        }

        for method_name, parameter_names in expected.items():
            with self.subTest(method=method_name):
                method = getattr(wechat_service.WeChatService, method_name)
                signature = inspect.signature(method)
                self.assertEqual(list(signature.parameters), parameter_names)

                if "exact" in signature.parameters:
                    self.assertIs(signature.parameters["exact"].default, False)
                if "wxname" in signature.parameters:
                    self.assertIsNone(signature.parameters["wxname"].default)
                if "who" in signature.parameters:
                    self.assertIsNone(signature.parameters["who"].default)

        chat_info_signature = inspect.signature(
            wechat_service.WeChatService.get_chat_info
        )
        self.assertIsNone(chat_info_signature.parameters["who"].default)

    def test_get_chat_info_calls_sdk_and_preserves_chat_data(self):
        response = _invoke(
            self.service.get_chat_info(
                who=None,
                exact=False,
                wxname="主账号",
            )
        )

        self.get_wechat.assert_called_once_with("主账号")
        self.switch_chat.assert_not_called()
        self.wx.ChatInfo.assert_called_once_with()
        self.assertTrue(response.success)
        self.assertIn("项目群", repr(response.data))
        self.assertIn("group_member_count", repr(response.data))

    def test_get_chat_info_can_switch_to_a_named_chat(self):
        response = _invoke(
            self.service.get_chat_info(
                who="项目群",
                exact=True,
                wxname="主账号",
            )
        )

        self.switch_chat.assert_called_once_with(
            self.wx,
            target="项目群",
            exact=True,
        )
        self.assertTrue(response.success)

    def test_group_operations_call_expected_sdk_methods(self):
        cases = [
            (
                "add_group_members",
                {"who": "项目群", "members": ["张三", "李四"], "exact": True},
                "AddGroupMembers",
                {"members": ["张三", "李四"]},
            ),
            (
                "set_group_name",
                {"who": "项目群", "value": "新群名", "exact": True},
                "SetGroupName",
                {"value": "新群名"},
            ),
            (
                "set_group_remark",
                {"who": "项目群", "value": "重要客户", "exact": True},
                "SetGroupRemark",
                {"value": "重要客户"},
            ),
            (
                "set_group_announcement",
                {"who": "项目群", "value": "今晚发布", "exact": True},
                "SetGroupAnnouncement",
                {"value": "今晚发布"},
            ),
            (
                "set_group_my_nickname",
                {"who": "项目群", "value": "值班同学", "exact": True},
                "SetGroupMyNickname",
                {"value": "值班同学"},
            ),
        ]

        for service_method, arguments, sdk_method, sdk_arguments in cases:
            with self.subTest(method=service_method):
                self.wx.reset_mock()
                self.get_wechat.reset_mock()
                self.switch_chat.reset_mock()
                self.switch_chat.return_value = True

                response = _invoke(
                    getattr(self.service, service_method)(
                        **arguments,
                        wxname="主账号",
                    )
                )

                self.get_wechat.assert_called_once_with("主账号")
                self.switch_chat.assert_called_once_with(
                    self.wx,
                    target="项目群",
                    exact=True,
                )
                getattr(self.wx, sdk_method).assert_called_once_with(**sdk_arguments)
                self.assertTrue(response.success)
                self.assertEqual(
                    self.service._queue.submissions[-1].get("max_retries"),
                    0,
                )

    def test_group_operations_without_who_use_the_current_group(self):
        cases = [
            ("add_group_members", {"members": ["张三"]}, "AddGroupMembers"),
            ("set_group_name", {"value": "新群名"}, "SetGroupName"),
            ("set_group_remark", {"value": "新备注"}, "SetGroupRemark"),
            (
                "set_group_announcement",
                {"value": "新公告"},
                "SetGroupAnnouncement",
            ),
            (
                "set_group_my_nickname",
                {"value": "新昵称"},
                "SetGroupMyNickname",
            ),
        ]

        for service_method, arguments, sdk_method in cases:
            with self.subTest(method=service_method):
                self.wx.reset_mock()
                self.switch_chat.reset_mock()

                response = _invoke(
                    getattr(self.service, service_method)(
                        **arguments,
                        wxname="主账号",
                    )
                )

                self.switch_chat.assert_not_called()
                self.wx.ChatInfo.assert_called_once_with()
                getattr(self.wx, sdk_method).assert_called_once()
                self.assertTrue(response.success)

    def test_empty_who_uses_the_current_group_without_switching(self):
        response = _invoke(
            self.service.set_group_name(
                who="",
                value="新群名",
                wxname="主账号",
            )
        )

        self.switch_chat.assert_not_called()
        self.wx.SetGroupName.assert_called_once_with(value="新群名")
        self.assertTrue(response.success)

    def test_create_group_calls_sdk_without_switching_chat(self):
        response = _invoke(
            self.service.create_group(
                contacts=["张三", "李四", "王五"],
                wxname="主账号",
            )
        )

        self.get_wechat.assert_called_once_with("主账号")
        self.switch_chat.assert_not_called()
        self.wx.CreateGroup.assert_called_once_with(
            contacts=["张三", "李四", "王五"]
        )
        self.assertTrue(response.success)
        self.assertEqual(
            self.service._queue.submissions[-1].get("max_retries"),
            0,
        )

    def test_failed_target_switch_skips_chat_info_and_group_mutations(self):
        cases = [
            ("get_chat_info", {}, "ChatInfo"),
            ("add_group_members", {"members": ["张三"]}, "AddGroupMembers"),
            ("set_group_name", {"value": "新群名"}, "SetGroupName"),
            ("set_group_remark", {"value": "备注"}, "SetGroupRemark"),
            (
                "set_group_announcement",
                {"value": "群公告"},
                "SetGroupAnnouncement",
            ),
            (
                "set_group_my_nickname",
                {"value": "群昵称"},
                "SetGroupMyNickname",
            ),
        ]

        self.switch_chat.return_value = False
        for service_method, extra_arguments, sdk_method in cases:
            with self.subTest(method=service_method):
                self.wx.reset_mock()
                self.get_wechat.reset_mock()
                self.switch_chat.reset_mock()
                self.switch_chat.return_value = False

                response = _invoke(
                    getattr(self.service, service_method)(
                        who="不存在的群",
                        exact=True,
                        wxname="主账号",
                        **extra_arguments,
                    )
                )

                getattr(self.wx, sdk_method).assert_not_called()
                self.assertFalse(response.success)

    def test_non_group_target_skips_group_mutation(self):
        self.wx.ChatInfo.return_value = {
            "chat_name": "张三",
            "chat_type": "friend",
        }

        response = _invoke(
            self.service.set_group_name(
                who="张三",
                value="新群名",
                exact=True,
                wxname="主账号",
            )
        )

        self.wx.SetGroupName.assert_not_called()
        self.assertFalse(response.success)
        self.assertEqual(response.data["error_code"], "GROUP_CHAT_REQUIRED")

    def test_sdk_failure_message_and_data_are_preserved(self):
        self.wx.SetGroupAnnouncement.return_value = _FailedWxResponse()

        response = _invoke(
            self.service.set_group_announcement(
                who="项目群",
                value="新公告",
                exact=True,
                wxname="主账号",
            )
        )

        self.assertFalse(response.success)
        self.assertEqual(response.message, "没有群管理权限")
        self.assertEqual(response.data, {"reason": "forbidden"})


class SafeChatHelperTests(unittest.TestCase):
    @patch.object(wechat_service.time, "sleep", return_value=None)
    def test_explicit_fuzzy_switch_accepts_the_sdk_selected_chat(self, _sleep):
        wx = MagicMock()
        wx.ChatInfo.return_value = {
            "chat_name": "项目交流群",
            "chat_type": "group",
        }

        result = wechat_service.safe_switch_chat(
            wx,
            target="项目",
            exact=False,
            max_retries=1,
        )

        self.assertTrue(result)
        wx.ChatWith.assert_called_once_with(who="项目", exact=False)

    @patch.object(wechat_service.time, "sleep", return_value=None)
    def test_legacy_switch_omits_exact_and_keeps_strict_name_check(self, _sleep):
        wx = MagicMock()
        wx.ChatInfo.return_value = {
            "chat_name": "项目群",
            "chat_type": "group",
        }

        result = wechat_service.safe_switch_chat(
            wx,
            target="项目群",
            max_retries=1,
        )

        self.assertTrue(result)
        wx.ChatWith.assert_called_once_with(who="项目群")


class WeChatGroupRouteTests(unittest.TestCase):
    EXPECTED_FIELDS = {
        "/chatinfo": {"who", "exact", "wxname"},
        "/group/members/add": {"who", "members", "exact", "wxname"},
        "/group/create": {"contacts", "wxname"},
        "/group/name": {"who", "value", "exact", "wxname"},
        "/group/remark": {"who", "value", "exact", "wxname"},
        "/group/announcement": {"who", "value", "exact", "wxname"},
        "/group/my-nickname": {"who", "value", "exact", "wxname"},
    }
    PLUS_ONLY_PATHS = {
        "/group/members/add",
        "/group/create",
        "/group/name",
        "/group/remark",
        "/group/announcement",
        "/group/my-nickname",
    }

    def test_expected_post_routes_exist(self):
        routes = {route.path: route for route in wechat_api.router.routes}

        for path in self.EXPECTED_FIELDS:
            with self.subTest(path=path):
                self.assertIn(path, routes)
                self.assertIn("POST", routes[path].methods)

    def test_plus_only_routes_have_the_official_star_marker(self):
        routes = {route.path: route for route in wechat_api.router.routes}

        for path in self.EXPECTED_FIELDS:
            with self.subTest(path=path):
                has_star = routes[path].summary.startswith("✨")
                self.assertEqual(has_star, path in self.PLUS_ONLY_PATHS)

    def test_route_request_models_expose_expected_fields(self):
        routes = {route.path: route for route in wechat_api.router.routes}

        for path, expected_fields in self.EXPECTED_FIELDS.items():
            with self.subTest(path=path):
                if path not in routes:
                    self.fail(f"missing route: {path}")

                request_parameter = inspect.signature(
                    routes[path].endpoint
                ).parameters["request"]
                request_model = request_parameter.annotation
                model_fields = getattr(request_model, "model_fields", None)
                if model_fields is None:
                    model_fields = getattr(request_model, "__fields__", {})
                self.assertEqual(set(model_fields), expected_fields)

    def test_group_request_models_allow_omitting_who(self):
        routes = {route.path: route for route in wechat_api.router.routes}
        payloads = {
            "/group/members/add": {"members": ["张三"]},
            "/group/name": {"value": "新群名"},
            "/group/remark": {"value": "新备注"},
            "/group/announcement": {"value": "新公告"},
            "/group/my-nickname": {"value": "新昵称"},
        }

        for path, payload in payloads.items():
            with self.subTest(path=path):
                request_model = inspect.signature(
                    routes[path].endpoint
                ).parameters["request"].annotation
                request = request_model(**payload)
                self.assertIsNone(request.who)


if __name__ == "__main__":
    unittest.main()
