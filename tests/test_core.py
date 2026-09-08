import json
import unittest

from wrongshell.core import inspect_command


class InspectCommandTests(unittest.TestCase):
    def test_powershell_makes_npm_shim_visible(self) -> None:
        report = inspect_command("npm ci", target_shell="powershell")

        self.assertEqual(report.target_shell, "powershell")
        self.assertEqual(report.translated, "npm.cmd ci")
        self.assertEqual(report.status, "ready")
        self.assertIn("PS-NPM-SHIM", {change.code for change in report.changes})
        self.assertIn("execution policy", report.changes[0].reason.lower())

    def test_bash_environment_assignment_becomes_explicit(self) -> None:
        report = inspect_command(
            "export API_URL=https://example.test\nnpm run build",
            source_shell="bash",
            target_shell="powershell",
        )

        self.assertIn('$env:API_URL="https://example.test"', report.translated)
        self.assertIn("npm.cmd run build", report.translated)
        self.assertEqual(report.status, "ready")

    def test_environment_assignment_does_not_swallow_next_command(self) -> None:
        report = inspect_command(
            "export API_URL=https://example.test; npm run build",
            source_shell="bash",
            target_shell="powershell",
        )

        self.assertEqual(
            report.translated,
            '$env:API_URL="https://example.test"; npm.cmd run build',
        )

    def test_destructive_translation_requires_review(self) -> None:
        report = inspect_command("rm -rf ./dist", source_shell="bash", target_shell="powershell")

        self.assertIn("Remove-Item -Recurse -Force ./dist", report.translated)
        self.assertEqual(report.status, "review")
        self.assertTrue(any(change.severity == "danger" for change in report.changes))

    def test_unknown_shell_construct_is_not_guessed(self) -> None:
        report = inspect_command("custom-tool --magic $(unknown)", target_shell="powershell")

        self.assertEqual(report.translated, report.original)
        self.assertEqual(report.status, "manual")
        self.assertTrue(report.blockers)

    def test_posix_command_stays_portable(self) -> None:
        report = inspect_command("python -m unittest", target_shell="bash")

        self.assertEqual(report.translated, report.original)
        self.assertEqual(report.status, "ready")
        self.assertFalse(report.changes)

    def test_report_is_json_serializable(self) -> None:
        report = inspect_command("npm ci", target_shell="powershell")

        payload = json.dumps(report.to_dict())
        decoded = json.loads(payload)
        self.assertEqual(decoded["translated"], "npm.cmd ci")
        self.assertEqual(decoded["changes"][0]["code"], "PS-NPM-SHIM")


if __name__ == "__main__":
    unittest.main()
