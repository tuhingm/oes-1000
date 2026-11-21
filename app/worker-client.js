export class OESWorkerClient {
  constructor(onStatus = () => {}) {
    this.worker = new Worker(new URL("../runtime/worker.js", import.meta.url), { type: "classic" });
    this.pending = new Map();
    this.sequence = 0;
    this.worker.onmessage = ({ data }) => {
      if (data.type === "status") { onStatus(data.text, "loading"); return; }
      if (data.type === "ready") { onStatus("Pyodide ready · " + data.version, "ready"); return; }
      const item = this.pending.get(data.id);
      if (!item) return;
      this.pending.delete(data.id);
      if (data.ok) item.resolve(data.result);
      else item.reject(new Error(data.error || "Worker request failed"));
    };
    this.worker.onerror = (event) => {
      onStatus(event.message || "Worker error", "error");
      for (const item of this.pending.values()) item.reject(new Error(event.message || "Worker error"));
      this.pending.clear();
    };
  }
  request(action, payload = {}) {
    const id = ++this.sequence;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.worker.postMessage({ id, action, payload });
    });
  }
  terminate() { this.worker.terminate(); }
}
