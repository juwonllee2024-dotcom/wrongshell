# Example

This deliberately small file represents a command block copied from an AI
answer. Inspect it without executing it:

```powershell
wrongshell --from-shell bash --shell powershell --file examples/ai-command.txt
```

Expected translation:

```text
$env:MODE="demo"
npm.cmd run build
```
