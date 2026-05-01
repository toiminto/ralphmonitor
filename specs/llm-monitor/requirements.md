# Requirements

## Q&A Record

### 1. LLM Backend
**Q:** What LLM backend is running at 192.168.100.134:8000?
**A:** llama.cpp server

### 2. Monitoring Architecture
**Q:** Should the monitor proxy requests or poll directly?
**A:** Proxy mode — monitor acts as reverse proxy between clients and LLM

### 3. Metrics to Track
**Q:** What specific metrics are needed?
**A:** All of the following:
- Token processing speed (tokens/sec for prompt + completion)
- Per-request latency (total time, prompt time, completion time)
- Token usage totals (prompt tokens, completion tokens, total tokens)
- Request count and success/failure rates
- GPU/CPU/VRAM usage from the LLM host
- Historical trends and charts over time
- Real-time live dashboard

### 4. Data Retention
**Q:** How long to retain data, and expected request volume?
**A:** Medium-term (1-4 weeks), 100-1000 requests/day

### 5. Technology Stack
**Q:** Preferred tech stack?
**A:** Open — pick what works best

### 6. Dashboard UI
**Q:** Simple or interactive dashboard?
**A:** Interactive dashboard with filters, date pickers, drill-downs

### 7. System Metrics Access
**Q:** How to access GPU/CPU/VRAM on the LLM host?
**A:** Monitor runs on the same machine as the LLM (local Docker)

### 8. Authentication
**Q:** Should the dashboard have auth?
**A:** No auth needed (local/trusted network)
