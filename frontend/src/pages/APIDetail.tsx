import { useState, useEffect, useMemo } from "react";
import { useParams } from "react-router-dom";
import api from "../services/api";
import {
  getAPI,
  type APIItem,
  listDeployments,
  createDeployment,
  deleteDeployment,
  type APIDeployment,
  listAuthPolicies,
  createAuthPolicy,
  deleteAuthPolicy,
  type AuthPolicy,
  listRateLimits,
  createRateLimit,
  deleteRateLimit,
  type RateLimit,
  listSchemas,
  createSchema,
  deleteSchema,
  type ApiSchema,
  listBackendPools,
  createBackendPool,
  deleteBackendPool,
  patchBackendHealth,
  type BackendPool,
} from "../services/apis";
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  TextField,
  Select,
  MenuItem,
  Button,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Chip,
  Alert,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  FormControl,
  InputLabel,
  Switch,
  Collapse,
  IconButton,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import { useQueryCache } from "../hooks/useQueryCache";
import { DetailPageSkeleton } from "../components/Skeletons";

type Route = {
  path: string;
  method: string;
  auth?: string;
  integration?: any;
  requestBodyModel?: string;
  validation?: string;
};

export default function APIDetail() {
  const params = useParams();
  const apiId = params.id ? Number(params.id) : null;

  const {
    data: apiData,
    loading,
    error,
  } = useQueryCache<APIItem>(`api-${apiId}`, () => getAPI(apiId!), {
    enabled: !!apiId,
  });

  const apiType = useMemo(() => {
    if (!apiData) return "rest";
    return apiData.config?._meta?.ui?.type || apiData.type || "rest";
  }, [apiData]);

  const routes = useMemo<Route[]>(() => {
    if (!apiData?.config?.routes || !Array.isArray(apiData.config.routes)) {
      return [{ path: "/", method: "GET", auth: "API Key" }];
    }
    return apiData.config.routes.map((r: any) => ({
      path: r.path || r.resource || "/",
      method: r.method || "GET",
      auth: r.auth || "API Key",
      integration: r.integration,
      requestBodyModel: r.requestBodyModel || r.schema,
      validation: r.validation,
    }));
  }, [apiData]);

  const [selectedRoute, setSelectedRoute] = useState<Route | null>(null);
  const [activeTab, setActiveTab] = useState(0);

  // Testing state
  const [method, setMethod] = useState("POST");
  const [path, setPath] = useState("/register");
  const [body, setBody] = useState(
    '{\n  "email": "test@example.com",\n  "password": "mypassword"\n}',
  );
  const [testApiKey, setTestApiKey] = useState("");
  const [response, setResponse] = useState<string>("");
  const [latency, setLatency] = useState<number | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  // Sub-resource state
  const [subLoading, setSubLoading] = useState(false);
  const [deployments, setDeployments] = useState<APIDeployment[]>([]);
  const [authPolicies, setAuthPolicies] = useState<AuthPolicy[]>([]);
  const [rateLimits, setRateLimits] = useState<RateLimit[]>([]);
  const [schemas, setSchemas] = useState<ApiSchema[]>([]);
  const [backendPools, setBackendPools] = useState<BackendPool[]>([]);

  // Create-form visibility
  const [dCreateOpen, setDCreateOpen] = useState(false);
  const [apCreateOpen, setApCreateOpen] = useState(false);
  const [rlCreateOpen, setRlCreateOpen] = useState(false);
  const [scCreateOpen, setScCreateOpen] = useState(false);
  const [bpCreateOpen, setBpCreateOpen] = useState(false);

  // Deployment form
  const [dEnvId, setDEnvId] = useState("");
  const [dUrlOverride, setDUrlOverride] = useState("");
  const [dNotes, setDNotes] = useState("");

  // Auth policy form
  const [apName, setApName] = useState("");
  const [apType, setApType] = useState("none");
  const [apConfig, setApConfig] = useState("{}");

  // Rate limit form
  const [rlAlgo, setRlAlgo] = useState("fixed_window");
  const [rlLimit, setRlLimit] = useState("100");
  const [rlWindow, setRlWindow] = useState("60");
  const [rlKeyType, setRlKeyType] = useState("global");

  // Schema form
  const [scName, setScName] = useState("");
  const [scDef, setScDef] = useState("{}");

  // Backend pool form
  const [bpName, setBpName] = useState("");
  const [bpAlgo, setBpAlgo] = useState("round_robin");
  const [bpBackends, setBpBackends] = useState(
    '[{"url":"","weight":1,"healthy":true}]',
  );

  // Select first route when routes change
  useEffect(() => {
    if (routes.length > 0 && !selectedRoute) {
      setSelectedRoute(routes[0]);
      setPath(routes[0].path);
      setMethod(routes[0].method);
    }
  }, [routes]);

  // Load sub-resource data when tab changes
  useEffect(() => {
    if (!apiId || activeTab === 0) return;
    setSubLoading(true);
    const loaders: Record<number, () => Promise<void>> = {
      1: () => listDeployments(apiId).then(setDeployments),
      2: () => listAuthPolicies(apiId).then(setAuthPolicies),
      3: () => listRateLimits(apiId).then(setRateLimits),
      4: () => listSchemas(apiId).then(setSchemas),
      5: () => listBackendPools(apiId).then(setBackendPools),
    };
    (loaders[activeTab]?.() ?? Promise.resolve())
      .catch(() => {})
      .finally(() => setSubLoading(false));
  }, [activeTab, apiId]);

  async function handleTest() {
    setResponse("");
    setTestError(null);
    const start = performance.now();
    try {
      const testPath = path.startsWith("/") ? path : `/${path}`;
      const requestData = body.trim() ? JSON.parse(body) : undefined;

      // Route through gateway instead of calling the integration URL directly
      const gwResponse = await api.request({
        method: method as any,
        url: `/gw/${apiId}${testPath}`,
        data: requestData,
        headers: testApiKey ? { "x-api-key": testApiKey } : {},
        validateStatus: () => true,
      });

      const end = performance.now();
      setLatency(Math.round(end - start));
      setResponse(JSON.stringify(gwResponse.data, null, 2));

      if (gwResponse.status >= 400) {
        setTestError(`HTTP ${gwResponse.status}: ${gwResponse.statusText}`);
      }
    } catch (err: any) {
      const end = performance.now();
      setLatency(Math.round(end - start));
      setTestError(err?.message || String(err));
      setResponse(String(err));
    }
  }

  const handleRouteSelect = (route: Route) => {
    setSelectedRoute(route);
    setPath(route.path);
    setMethod(route.method);
    setResponse("");
    setLatency(null);
    setTestError(null);
  };

  // ── Sub-resource action helpers ──────────────────────────────────────────

  async function handleCreateDeployment() {
    if (!apiId || !dEnvId) return;
    await createDeployment(apiId, {
      environment_id: Number(dEnvId),
      target_url_override: dUrlOverride || undefined,
      notes: dNotes || undefined,
    });
    setDCreateOpen(false);
    setDEnvId("");
    setDUrlOverride("");
    setDNotes("");
    listDeployments(apiId).then(setDeployments);
  }

  async function handleDeleteDeployment(id: number) {
    if (!apiId) return;
    await deleteDeployment(apiId, id);
    setDeployments((d) => d.filter((x) => x.id !== id));
  }

  async function handleCreateAuthPolicy() {
    if (!apiId || !apName) return;
    let config: Record<string, any> = {};
    try {
      config = JSON.parse(apConfig);
    } catch {}
    await createAuthPolicy(apiId, {
      name: apName,
      type: apType as any,
      config,
    });
    setApCreateOpen(false);
    setApName("");
    setApType("none");
    setApConfig("{}");
    listAuthPolicies(apiId).then(setAuthPolicies);
  }

  async function handleDeleteAuthPolicy(id: number) {
    if (!apiId) return;
    await deleteAuthPolicy(apiId, id);
    setAuthPolicies((d) => d.filter((x) => x.id !== id));
  }

  async function handleCreateRateLimit() {
    if (!apiId) return;
    await createRateLimit(apiId, {
      algorithm: rlAlgo,
      limit: Number(rlLimit),
      window_seconds: Number(rlWindow),
      key_type: rlKeyType,
    });
    setRlCreateOpen(false);
    setRlAlgo("fixed_window");
    setRlLimit("100");
    setRlWindow("60");
    setRlKeyType("global");
    listRateLimits(apiId).then(setRateLimits);
  }

  async function handleDeleteRateLimit(id: number) {
    if (!apiId) return;
    await deleteRateLimit(apiId, id);
    setRateLimits((d) => d.filter((x) => x.id !== id));
  }

  async function handleCreateSchema() {
    if (!apiId || !scName) return;
    let definition: object = {};
    try {
      definition = JSON.parse(scDef);
    } catch {}
    await createSchema(apiId, { name: scName, definition });
    setScCreateOpen(false);
    setScName("");
    setScDef("{}");
    listSchemas(apiId).then(setSchemas);
  }

  async function handleDeleteSchema(id: number) {
    if (!apiId) return;
    await deleteSchema(apiId, id);
    setSchemas((d) => d.filter((x) => x.id !== id));
  }

  async function handleCreateBackendPool() {
    if (!apiId || !bpName) return;
    let backends: object[] = [];
    try {
      backends = JSON.parse(bpBackends);
    } catch {}
    await createBackendPool(apiId, {
      name: bpName,
      algorithm: bpAlgo,
      backends,
    });
    setBpCreateOpen(false);
    setBpName("");
    setBpAlgo("round_robin");
    setBpBackends('[{"url":"","weight":1,"healthy":true}]');
    listBackendPools(apiId).then(setBackendPools);
  }

  async function handleDeleteBackendPool(id: number) {
    if (!apiId) return;
    await deleteBackendPool(apiId, id);
    setBackendPools((d) => d.filter((x) => x.id !== id));
  }

  async function handleToggleBackendHealth(
    pool: BackendPool,
    url: string,
    healthy: boolean,
  ) {
    if (!apiId) return;
    const updated = await patchBackendHealth(apiId, pool.id, url, healthy);
    setBackendPools((d) => d.map((p) => (p.id === updated.id ? updated : p)));
  }

  if (loading) {
    return <DetailPageSkeleton />;
  }

  if (error || !apiData) {
    return (
      <Container maxWidth="lg" sx={{ py: 2 }}>
        <Alert severity="error">Error: {error || "API not found"}</Alert>
      </Container>
    );
  }

  // ── Tab panels ───────────────────────────────────────────────────────────

  const SubResourcePanel = ({ children }: { children: React.ReactNode }) => (
    <Paper sx={{ p: 2, mt: 2 }} elevation={1}>
      {subLoading ? (
        <Typography color="text.secondary">Loading…</Typography>
      ) : (
        children
      )}
    </Paper>
  );

  const deploymentsTab = (
    <SubResourcePanel>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
        <Typography variant="h6">Deployments</Typography>
        <Button
          startIcon={<AddIcon />}
          size="small"
          onClick={() => setDCreateOpen((v) => !v)}
        >
          Deploy
        </Button>
      </Box>
      <Collapse in={dCreateOpen}>
        <Paper
          sx={{ p: 2, mb: 2, bgcolor: "background.default" }}
          elevation={0}
        >
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <TextField
              label="Environment ID"
              value={dEnvId}
              onChange={(e) => setDEnvId(e.target.value)}
              size="small"
              type="number"
              sx={{ width: 150 }}
            />
            <TextField
              label="Target URL Override"
              value={dUrlOverride}
              onChange={(e) => setDUrlOverride(e.target.value)}
              size="small"
              sx={{ flex: 1, minWidth: 200 }}
            />
            <TextField
              label="Notes"
              value={dNotes}
              onChange={(e) => setDNotes(e.target.value)}
              size="small"
              sx={{ flex: 1, minWidth: 200 }}
            />
            <Button
              variant="contained"
              size="small"
              onClick={handleCreateDeployment}
            >
              Create
            </Button>
          </Box>
        </Paper>
      </Collapse>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Environment</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>URL Override</TableCell>
            <TableCell>Deployed At</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {deployments.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} align="center">
                <Typography color="text.secondary" variant="body2">
                  No deployments
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            deployments.map((d) => (
              <TableRow key={d.id}>
                <TableCell>{d.id}</TableCell>
                <TableCell>{d.environment_id}</TableCell>
                <TableCell>
                  <Chip
                    label={d.status}
                    size="small"
                    color={d.status === "active" ? "success" : "default"}
                  />
                </TableCell>
                <TableCell
                  sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}
                >
                  {d.target_url_override || "—"}
                </TableCell>
                <TableCell>
                  {d.deployed_at
                    ? new Date(d.deployed_at).toLocaleString()
                    : "—"}
                </TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => handleDeleteDeployment(d.id)}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </SubResourcePanel>
  );

  const authPoliciesTab = (
    <SubResourcePanel>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
        <Typography variant="h6">Auth Policies</Typography>
        <Button
          startIcon={<AddIcon />}
          size="small"
          onClick={() => setApCreateOpen((v) => !v)}
        >
          Add
        </Button>
      </Box>
      <Collapse in={apCreateOpen}>
        <Paper
          sx={{ p: 2, mb: 2, bgcolor: "background.default" }}
          elevation={0}
        >
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <TextField
              label="Name"
              value={apName}
              onChange={(e) => setApName(e.target.value)}
              size="small"
              sx={{ width: 160 }}
            />
            <FormControl size="small" sx={{ width: 140 }}>
              <InputLabel>Type</InputLabel>
              <Select
                label="Type"
                value={apType}
                onChange={(e) => setApType(e.target.value)}
              >
                {["none", "open", "apiKey", "jwt", "bearer", "oauth2"].map(
                  (t) => (
                    <MenuItem key={t} value={t}>
                      {t}
                    </MenuItem>
                  ),
                )}
              </Select>
            </FormControl>
            <TextField
              label="Config (JSON)"
              value={apConfig}
              onChange={(e) => setApConfig(e.target.value)}
              size="small"
              sx={{ flex: 1, minWidth: 200, fontFamily: "monospace" }}
            />
            <Button
              variant="contained"
              size="small"
              onClick={handleCreateAuthPolicy}
            >
              Create
            </Button>
          </Box>
        </Paper>
      </Collapse>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Type</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {authPolicies.length === 0 ? (
            <TableRow>
              <TableCell colSpan={3} align="center">
                <Typography color="text.secondary" variant="body2">
                  No auth policies
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            authPolicies.map((p) => (
              <TableRow key={p.id}>
                <TableCell>{p.name}</TableCell>
                <TableCell>
                  <Chip label={p.type} size="small" />
                </TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => handleDeleteAuthPolicy(p.id)}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </SubResourcePanel>
  );

  const rateLimitsTab = (
    <SubResourcePanel>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
        <Typography variant="h6">Rate Limits</Typography>
        <Button
          startIcon={<AddIcon />}
          size="small"
          onClick={() => setRlCreateOpen((v) => !v)}
        >
          Add
        </Button>
      </Box>
      <Collapse in={rlCreateOpen}>
        <Paper
          sx={{ p: 2, mb: 2, bgcolor: "background.default" }}
          elevation={0}
        >
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <FormControl size="small" sx={{ width: 150 }}>
              <InputLabel>Algorithm</InputLabel>
              <Select
                label="Algorithm"
                value={rlAlgo}
                onChange={(e) => setRlAlgo(e.target.value)}
              >
                {["fixed_window", "sliding_window", "token_bucket"].map((a) => (
                  <MenuItem key={a} value={a}>
                    {a}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="Limit"
              value={rlLimit}
              onChange={(e) => setRlLimit(e.target.value)}
              size="small"
              type="number"
              sx={{ width: 90 }}
            />
            <TextField
              label="Window (s)"
              value={rlWindow}
              onChange={(e) => setRlWindow(e.target.value)}
              size="small"
              type="number"
              sx={{ width: 100 }}
            />
            <FormControl size="small" sx={{ width: 130 }}>
              <InputLabel>Key Type</InputLabel>
              <Select
                label="Key Type"
                value={rlKeyType}
                onChange={(e) => setRlKeyType(e.target.value)}
              >
                {["global", "ip", "user", "api_key"].map((k) => (
                  <MenuItem key={k} value={k}>
                    {k}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              variant="contained"
              size="small"
              onClick={handleCreateRateLimit}
            >
              Create
            </Button>
          </Box>
        </Paper>
      </Collapse>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Algorithm</TableCell>
            <TableCell>Limit</TableCell>
            <TableCell>Window (s)</TableCell>
            <TableCell>Key Type</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {rateLimits.length === 0 ? (
            <TableRow>
              <TableCell colSpan={5} align="center">
                <Typography color="text.secondary" variant="body2">
                  No rate limits
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            rateLimits.map((r) => (
              <TableRow key={r.id}>
                <TableCell>
                  <Chip label={r.algorithm} size="small" />
                </TableCell>
                <TableCell>{r.limit}</TableCell>
                <TableCell>{r.window_seconds}</TableCell>
                <TableCell>{r.key_type}</TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => handleDeleteRateLimit(r.id)}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </SubResourcePanel>
  );

  const schemasTab = (
    <SubResourcePanel>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
        <Typography variant="h6">Schemas</Typography>
        <Button
          startIcon={<AddIcon />}
          size="small"
          onClick={() => setScCreateOpen((v) => !v)}
        >
          Add
        </Button>
      </Box>
      <Collapse in={scCreateOpen}>
        <Paper
          sx={{ p: 2, mb: 2, bgcolor: "background.default" }}
          elevation={0}
        >
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <TextField
              label="Name"
              value={scName}
              onChange={(e) => setScName(e.target.value)}
              size="small"
              sx={{ width: 160 }}
            />
            <TextField
              label="JSON Schema Definition"
              value={scDef}
              onChange={(e) => setScDef(e.target.value)}
              multiline
              minRows={3}
              size="small"
              sx={{ flex: 1, minWidth: 300, fontFamily: "monospace" }}
            />
            <Button
              variant="contained"
              size="small"
              onClick={handleCreateSchema}
              sx={{ alignSelf: "flex-start" }}
            >
              Create
            </Button>
          </Box>
        </Paper>
      </Collapse>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Definition (preview)</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {schemas.length === 0 ? (
            <TableRow>
              <TableCell colSpan={3} align="center">
                <Typography color="text.secondary" variant="body2">
                  No schemas
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            schemas.map((s) => (
              <TableRow key={s.id}>
                <TableCell>{s.name}</TableCell>
                <TableCell
                  sx={{
                    fontFamily: "monospace",
                    fontSize: "0.75rem",
                    maxWidth: 400,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {s.definition
                    ? JSON.stringify(s.definition).slice(0, 80)
                    : s.raw?.slice(0, 80) || "—"}
                </TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => handleDeleteSchema(s.id)}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </SubResourcePanel>
  );

  const backendPoolsTab = (
    <SubResourcePanel>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
        <Typography variant="h6">Backend Pools</Typography>
        <Button
          startIcon={<AddIcon />}
          size="small"
          onClick={() => setBpCreateOpen((v) => !v)}
        >
          Add
        </Button>
      </Box>
      <Collapse in={bpCreateOpen}>
        <Paper
          sx={{ p: 2, mb: 2, bgcolor: "background.default" }}
          elevation={0}
        >
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <TextField
              label="Pool Name"
              value={bpName}
              onChange={(e) => setBpName(e.target.value)}
              size="small"
              sx={{ width: 160 }}
            />
            <FormControl size="small" sx={{ width: 160 }}>
              <InputLabel>Algorithm</InputLabel>
              <Select
                label="Algorithm"
                value={bpAlgo}
                onChange={(e) => setBpAlgo(e.target.value)}
              >
                {["round_robin", "weighted", "least_connections", "random"].map(
                  (a) => (
                    <MenuItem key={a} value={a}>
                      {a}
                    </MenuItem>
                  ),
                )}
              </Select>
            </FormControl>
            <TextField
              label="Backends (JSON array)"
              value={bpBackends}
              onChange={(e) => setBpBackends(e.target.value)}
              multiline
              minRows={3}
              size="small"
              sx={{ flex: 1, minWidth: 300, fontFamily: "monospace" }}
              helperText='e.g. [{"url":"http://...","weight":1,"healthy":true}]'
            />
            <Button
              variant="contained"
              size="small"
              onClick={handleCreateBackendPool}
              sx={{ alignSelf: "flex-start" }}
            >
              Create
            </Button>
          </Box>
        </Paper>
      </Collapse>
      {backendPools.map((pool) => (
        <Paper
          key={pool.id}
          sx={{ mb: 2, p: 2, bgcolor: "background.default" }}
          elevation={0}
        >
          <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
            <Typography variant="subtitle1" fontWeight={600}>
              {pool.name}
              <Chip label={pool.algorithm} size="small" sx={{ ml: 1 }} />
            </Typography>
            <IconButton
              size="small"
              onClick={() => handleDeleteBackendPool(pool.id)}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Box>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>URL</TableCell>
                <TableCell>Weight</TableCell>
                <TableCell>Healthy</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {pool.backends.map((b) => (
                <TableRow key={b.url}>
                  <TableCell
                    sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}
                  >
                    {b.url}
                  </TableCell>
                  <TableCell>{b.weight}</TableCell>
                  <TableCell>
                    <Switch
                      size="small"
                      checked={b.healthy}
                      onChange={(e) =>
                        handleToggleBackendHealth(pool, b.url, e.target.checked)
                      }
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      ))}
      {backendPools.length === 0 && !bpCreateOpen && (
        <Typography color="text.secondary" variant="body2" sx={{ mt: 1 }}>
          No backend pools. Click "Add" to create one.
        </Typography>
      )}
    </SubResourcePanel>
  );

  const tabPanels: Record<number, React.ReactElement> = {
    1: deploymentsTab,
    2: authPoliciesTab,
    3: rateLimitsTab,
    4: schemasTab,
    5: backendPoolsTab,
  };

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      {/* Tab navigation */}
      <Paper sx={{ mb: 2 }} elevation={1}>
        <Tabs
          value={activeTab}
          onChange={(_, v) => setActiveTab(v)}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="Overview" />
          <Tab label="Deployments" />
          <Tab label="Auth Policies" />
          <Tab label="Rate Limits" />
          <Tab label="Schemas" />
          <Tab label="Backend Pools" />
        </Tabs>
      </Paper>

      {/* Sub-resource tabs (1-5) */}
      {activeTab !== 0 && tabPanels[activeTab]}

      {/* Overview tab (0) */}
      {activeTab === 0 && (
        <Grid container spacing={2}>
          {/* Left Sidebar - Routes List */}
          <Grid item xs={12} md={3}>
            <Paper
              sx={{ p: 2, bgcolor: "background.paper", color: "text.primary" }}
              elevation={1}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 1,
                }}
              >
                <Typography variant="h6" gutterBottom>
                  {apiData.name}
                </Typography>
                <Chip
                  label={apiType === "rest" ? "REST" : "GraphQL"}
                  size="small"
                  color={apiType === "rest" ? "primary" : "secondary"}
                />
              </Box>
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
                gutterBottom
              >
                v{apiData.version}
              </Typography>
              <List component="nav" sx={{ mt: 2 }}>
                {routes.map((route, index) => (
                  <ListItem key={index} disablePadding>
                    <ListItemButton
                      selected={
                        selectedRoute?.path === route.path &&
                        selectedRoute?.method === route.method
                      }
                      onClick={() => handleRouteSelect(route)}
                    >
                      <ListItemText
                        primary={
                          <Box>
                            <Chip
                              label={route.method}
                              size="small"
                              color={
                                apiType === "rest" ? "primary" : "secondary"
                              }
                              sx={{ mr: 1, minWidth: 60 }}
                            />
                            {route.path}
                          </Box>
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            </Paper>
          </Grid>

          {/* Middle - Route Details */}
          <Grid item xs={12} md={6}>
            <Paper
              sx={{ p: 2, bgcolor: "background.paper", color: "text.primary" }}
              elevation={1}
            >
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 2,
                }}
              >
                <Typography variant="h6">
                  <Chip
                    label={selectedRoute?.method || "GET"}
                    size="small"
                    color={apiType === "rest" ? "primary" : "secondary"}
                    sx={{ mr: 1 }}
                  />
                  {selectedRoute?.path || "/"}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {apiData.name} / {apiId}
                </Typography>
              </Box>

              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: "1fr",
                  gap: 2,
                  mt: 2,
                }}
              >
                {/* Method Request */}
                <Paper
                  sx={{ p: 2, bgcolor: "background.default" }}
                  elevation={0}
                >
                  <Typography variant="subtitle1" gutterBottom>
                    {apiType === "rest"
                      ? "Method Request"
                      : "Operation Details"}
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    {apiType === "rest" ? (
                      <>
                        <Box
                          sx={{
                            display: "flex",
                            justifyContent: "space-between",
                            mb: 1,
                          }}
                        >
                          <Typography>Authorization</Typography>
                          <Typography color="text.secondary">
                            {selectedRoute?.auth || "NONE"}
                          </Typography>
                        </Box>
                        {selectedRoute?.requestBodyModel && (
                          <Box
                            sx={{
                              display: "flex",
                              justifyContent: "space-between",
                              mt: 1,
                            }}
                          >
                            <Typography>Request Body Model</Typography>
                            <Typography color="text.secondary">
                              {selectedRoute.requestBodyModel}
                            </Typography>
                          </Box>
                        )}
                      </>
                    ) : (
                      <>
                        <Box
                          sx={{
                            display: "flex",
                            justifyContent: "space-between",
                            mb: 1,
                          }}
                        >
                          <Typography>Operation Type</Typography>
                          <Typography color="text.secondary">
                            {selectedRoute?.method || "QUERY"}
                          </Typography>
                        </Box>
                        <Box
                          sx={{
                            display: "flex",
                            justifyContent: "space-between",
                            mt: 1,
                          }}
                        >
                          <Typography>Resolver</Typography>
                          <Typography
                            color="text.secondary"
                            sx={{
                              maxWidth: 300,
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}
                          >
                            {selectedRoute?.integration?.url || "—"}
                          </Typography>
                        </Box>
                      </>
                    )}
                  </Box>
                </Paper>

                {/* Request Validation */}
                <Paper
                  sx={{ p: 2, bgcolor: "background.default" }}
                  elevation={0}
                >
                  <Typography variant="subtitle1" gutterBottom>
                    {apiType === "rest"
                      ? "Request Validation"
                      : "Schema Validation"}
                  </Typography>
                  <Typography color="text.secondary">
                    {selectedRoute?.validation ||
                      (apiType === "rest"
                        ? "Params Body: None"
                        : "Schema: None")}
                  </Typography>
                </Paper>

                {/* Logs */}
                <Paper
                  sx={{ p: 2, bgcolor: "background.default" }}
                  elevation={0}
                >
                  <Typography variant="subtitle1" gutterBottom>
                    Logs
                  </Typography>
                  <Box
                    component="pre"
                    sx={{
                      whiteSpace: "pre-wrap",
                      fontFamily: "monospace",
                      fontSize: "0.875rem",
                      m: 0,
                      p: 1,
                      bgcolor: "background.paper",
                      borderRadius: 1,
                    }}
                  >
                    {apiType === "rest"
                      ? `START Request
Received request: ${selectedRoute?.path || "/"}
Authorization: ${selectedRoute?.auth || "NONE"}
END Request`
                      : `START ${selectedRoute?.method || "QUERY"}
Operation: ${selectedRoute?.path || "/"}
Resolver: ${selectedRoute?.integration?.url || "Not configured"}
END ${selectedRoute?.method || "QUERY"}`}
                  </Box>
                </Paper>
              </Box>
            </Paper>
          </Grid>

          {/* Right Sidebar - Testing */}
          <Grid item xs={12} md={3}>
            <Paper
              sx={{
                p: 2,
                bgcolor: "background.paper",
                color: "text.primary",
                position: "sticky",
                top: 16,
              }}
              elevation={1}
            >
              <Typography variant="h6" gutterBottom>
                Test via Gateway
              </Typography>

              <Alert severity="info" sx={{ mb: 1, fontSize: "0.75rem" }}>
                <Typography variant="caption" display="block">
                  Requests are routed through <code>/gw/{apiId}/…</code>
                </Typography>
              </Alert>

              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 1.5,
                  mt: 2,
                }}
              >
                <Select
                  size="small"
                  value={method}
                  onChange={(e) => setMethod(e.target.value as string)}
                  fullWidth
                >
                  {apiType === "rest" ? (
                    <>
                      <MenuItem value="GET">GET</MenuItem>
                      <MenuItem value="POST">POST</MenuItem>
                      <MenuItem value="PUT">PUT</MenuItem>
                      <MenuItem value="PATCH">PATCH</MenuItem>
                      <MenuItem value="DELETE">DELETE</MenuItem>
                    </>
                  ) : (
                    <>
                      <MenuItem value="QUERY">Query</MenuItem>
                      <MenuItem value="MUTATION">Mutation</MenuItem>
                      <MenuItem value="SUBSCRIPTION">Subscription</MenuItem>
                    </>
                  )}
                </Select>

                <TextField
                  label={apiType === "rest" ? "Path" : "Operation Path"}
                  value={path}
                  onChange={(e) => setPath(e.target.value)}
                  size="small"
                  fullWidth
                  helperText={
                    apiType === "graphql" ? "e.g., /graphql" : undefined
                  }
                />

                <TextField
                  label="API Key (optional)"
                  value={testApiKey}
                  onChange={(e) => setTestApiKey(e.target.value)}
                  size="small"
                  fullWidth
                  placeholder="x-api-key header value"
                />

                <TextField
                  label={apiType === "rest" ? "Request Body" : "Query/Mutation"}
                  multiline
                  minRows={5}
                  maxRows={8}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  size="small"
                  fullWidth
                  placeholder={
                    apiType === "graphql"
                      ? "{\n  query {\n    user(id: 1) {\n      name\n      email\n    }\n  }\n}"
                      : undefined
                  }
                  sx={{ fontFamily: "monospace", fontSize: "0.875rem" }}
                />

                <Button variant="contained" onClick={handleTest} fullWidth>
                  Test
                </Button>

                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Latency: {latency !== null ? `${latency} ms` : "—"}
                  </Typography>
                </Box>

                {testError && (
                  <Alert severity="error" sx={{ fontSize: "0.75rem" }}>
                    {testError}
                  </Alert>
                )}

                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    Response
                  </Typography>
                  <Box
                    component="pre"
                    sx={{
                      whiteSpace: "pre-wrap",
                      fontFamily: "monospace",
                      fontSize: "0.75rem",
                      maxHeight: 300,
                      overflow: "auto",
                      m: 0,
                      p: 1,
                      bgcolor: "background.default",
                      borderRadius: 1,
                      border: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    {response || "// Response will appear here"}
                  </Box>
                </Box>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      )}
    </Container>
  );
}
