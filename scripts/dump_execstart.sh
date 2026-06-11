#!/usr/bin/env bash
for u in mcp dashboard bytewax decay narrator watcher llamacpp otel; do
  echo "== findevil-$u =="
  grep -hE 'ExecStart|EnvironmentFile' "/etc/systemd/system/findevil-$u.service" 2>/dev/null
done
echo "== findevil CLI subcommands =="
/opt/findevil/venv/bin/findevil --help 2>&1 | sed -n '1,40p'
