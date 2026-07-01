from types import SimpleNamespace
import unittest

import artbot.shared as shared


class PermissionTest(unittest.TestCase):
    def test_mod_role_check_is_case_and_whitespace_insensitive(self) -> None:
        member = SimpleNamespace(
            id=123,
            guild_permissions=SimpleNamespace(administrator=False),
            roles=[SimpleNamespace(name="  BOT MODERATOR  ")],
        )

        self.assertTrue(shared.has_admin_or_mod_permissions(member))

    def test_mod_id_passes_without_guild_permissions_or_roles(self) -> None:
        member = SimpleNamespace(id=shared.MOD_IDS[0])

        self.assertTrue(shared.has_admin_or_mod_permissions(member))

    def test_plain_user_without_permissions_does_not_crash(self) -> None:
        member = SimpleNamespace(id=123, roles=[])

        self.assertFalse(shared.has_admin_or_mod_permissions(member))

    def test_named_role_helper_normalizes_names(self) -> None:
        member = SimpleNamespace(roles=[SimpleNamespace(name=" DAILIES CHALLENGER ")])

        self.assertTrue(shared.has_named_role(member, ["dailies challenger"]))


if __name__ == "__main__":
    unittest.main()
