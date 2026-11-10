import unittest

from google.adk.errors.session_not_found_error import SessionNotFoundError

from adk_session_bound_tools.demo import APP_NAME, build_runner, run_lookup


class SessionBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.runner = build_runner()
        self.alex = await self.runner.session_service.create_session(
            app_name=APP_NAME, user_id="alex"
        )
        self.robin = await self.runner.session_service.create_session(
            app_name=APP_NAME, user_id="robin"
        )

    async def lookup(
        self, user_id: str, session_id: str, order_id: str
    ) -> dict[str, str]:
        return await run_lookup(
            self.runner, user_id=user_id, session_id=session_id, order_id=order_id
        )

    async def test_caller_can_read_own_order(self) -> None:
        result = await self.lookup("alex", self.alex.id, "ord-1001")
        self.assertEqual(
            result,
            {
                "outcome": "found",
                "order_id": "ord-1001",
                "delivery_status": "in_transit",
            },
        )

    async def test_cross_account_and_unknown_references_look_the_same(self) -> None:
        other = await self.lookup("alex", self.alex.id, "ord-2001")
        missing = await self.lookup("alex", self.alex.id, "ord-9999")
        self.assertEqual(other, {"outcome": "not_found"})
        self.assertEqual(missing, other)
        owner = await self.lookup("robin", self.robin.id, "ord-2001")
        self.assertEqual(owner["delivery_status"], "delivered")

    async def test_session_belongs_to_its_original_caller(self) -> None:
        with self.assertRaises(SessionNotFoundError):
            await self.lookup("robin", self.alex.id, "ord-1001")
