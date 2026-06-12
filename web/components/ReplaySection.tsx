"use client";

import { useEffect, useState } from "react";
import ReplayViewer from "./ReplayViewer";

export default function ReplaySection() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    fetch("/data/rocba_run.json")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setData)
      .catch(() => setErr(true));
  }, []);

  if (err) {
    return (
      <ReplayViewer data={{ dataset: "", tool: "", frames: [] }} />
    );
  }
  if (!data) {
    return (
      <div className="rounded-2xl border border-edge bg-panel/60 p-10 text-center text-muted">
        Loading real-run replay…
      </div>
    );
  }
  return <ReplayViewer data={data} />;
}
