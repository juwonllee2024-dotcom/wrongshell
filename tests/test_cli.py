import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from wrongshell.cli import main


class CliTests(unittest.TestCase):
    def test_json_output_is_scriptable(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--shell", "powershell", "--format", "json", "npm", "ci"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["translated"], "npm.cmd ci")

    def test_file_input_preserves_multiline_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ai-command.txt"
            path.write_text("export MODE=demo\nnpm run build\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    ["--shell", "powershell", "--from-shell", "bash", "--file", str(path)]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn('$env:MODE="demo"', output.getvalue())
        self.assertIn("npm.cmd run build", output.getvalue())


if __name__ == "__main__":
    unittest.main()
