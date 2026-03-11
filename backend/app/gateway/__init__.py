"""Gateway proxy engine — data plane for registered APIs.

URL pattern:  /gw/{api_id}/{path:path}

Pipeline (in order):
  1. Resolve API record from the registry
  2. Enforce AuthPolicy  (apiKey / jwt / none)
  3. Enforce RateLimit   (per-ip / per-key / global)
  4. Proxy request to upstream target_url via httpx
  5. Return upstream response with X-Gateway-* headers
"""
