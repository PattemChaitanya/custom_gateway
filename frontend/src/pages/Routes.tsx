import { useEffect, useMemo, useState } from "react";
import { useParams, Link as RouterLink, useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Button,
  Select,
  MenuItem,
  TextField,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Chip,
  Checkbox,
  FormControlLabel,
} from "@mui/material";
import { listAPIs } from "../services/apis";

type RouteRow = {
  resource: string;
  method: string;
  auth: string;
  integration: string;
};

const SAMPLE: RouteRow[] = [
  {
    resource: "/user/register",
    method: "ANY",
    auth: "API Key",
    integration: "Lambda Function",
  },
  {
    resource: "/user/login",
    method: "POST",
    auth: "API Key",
    integration: "Lambda Function",
  },
  {
    resource: "/user/{id}",
    method: "GET",
    auth: "API Key",
    integration: "HTTP Backend",
  },
  {
    resource: "/user/{id}",
    method: "PATCH",
    auth: "API Key",
    integration: "Lambda Function",
  },
  {
    resource: "/task",
    method: "PUT",
    auth: "API Key",
    integration: "HTTP Backend",
  },
  {
    resource: "/task/{id}",
    method: "POST",
    auth: "API Key",
    integration: "Lambda Function",
  },
  {
    resource: "/authenticate",
    method: "GET",
    auth: "API Key",
    integration: "HTTP Backend",
  },
  {
    resource: "/auth/token",
    method: "POST",
    auth: "JWT",
    integration: "HTTP Backend",
  },
  {
    resource: "/profile",
    method: "GET",
    auth: "GET",
    integration: "HTTP Backend",
  },
  {
    resource: "/metrics",
    method: "GET",
    auth: "GET",
    integration: "HTTP Backend",
  },
  {
    resource: "/config",
    method: "GET",
    auth: "GET",
    integration: "HTTP Backend",
  },
  {
    resource: "/settings",
    method: "GET",
    auth: "GET",
    integration: "HTTP Backend",
  },
];

export default function Routes() {
  const { id } = useParams();
  const navigate = useNavigate();
  // config mode: resource (form), json, yaml, terraform
  const [configMode, setConfigMode] = useState<
    "resource" | "json" | "yaml" | "terraform"
  >("resource");
  // GraphQL toggle hides REST UI and shows GraphQL editor
  const [isGraphQL, setIsGraphQL] = useState(false);
  const [filter, setFilter] = useState("");
  const [showCount, setShowCount] = useState(50);

  // rowsData === null -> still loading; [] -> loaded but no apis
  const [rowsData, setRowsData] = useState<RouteRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // canonical normalized schema shared across editors
  const [canonical, setCanonical] = useState<any | null>(null);
  // editors' raw text
  const [jsonText, setJsonText] = useState("");
  const [yamlText, setYamlText] = useState("");
  const [tfText, setTfText] = useState("");
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Fetch routes from server for the given API id. If the fetch fails we fall back to SAMPLE.
  useEffect(() => {
    let mounted = true;
    setRowsData(null);
    setError(null);

    (async () => {
      try {
        const res = await listAPIs();
        if (!mounted) return;
        // normalize the API response to RouteRow[] so the state type matches
        let rows: RouteRow[];
        if (Array.isArray(res)) {
          rows = (res as any[]).map((item: any) => ({
            resource: item.resource ?? item.path ?? item.name ?? "",
            method: item.method ?? "ANY",
            auth: item.auth ?? "API Key",
            integration: item.integration ?? "HTTP Backend",
          }));
        } else {
          rows = SAMPLE.slice();
        }
        setRowsData(rows);
        // initialize canonical schema from rows
        const initialCanonical = rowsToCanonical(rows, id || "MyAPI");
        setCanonical(initialCanonical);
        setJsonText(JSON.stringify(initialCanonical, null, 2));
        setYamlText(canonicalToYAML(initialCanonical));
      } catch (e: any) {
        if (!mounted) return;
        setError(e?.message ?? String(e));
        setRowsData([]);
      }
    })();

    return () => {
      mounted = false;
    };
  }, []);

  // live-validate canonical whenever it changes
  useEffect(() => {
    if (!canonical) return;
    const errs = validateCanonical(canonical);
    setValidationErrors(errs);
  }, [canonical]);

  const rows = useMemo(() => {
    const source = rowsData === null ? [] : rowsData;
    if (!filter) return source.slice(0, showCount);
    const f = filter.toLowerCase();
    return source
      .filter(
        (r) =>
          r.resource.toLowerCase().includes(f) ||
          r.method.toLowerCase().includes(f),
      )
      .slice(0, showCount);
  }, [filter, showCount, rowsData]);

  // Navigation handlers
  const handleCreate = () => {
    navigate(`/apis/create`);
  };

  const handleEdit = (r: RouteRow, index: number) => {
    console.log(index, "index", r);
    const apiId = index || "MyAPI";
    // encode resource so it can be safely used in the URL
    // const resourceKey = encodeURIComponent(r.resource.replace(/\//g, '_'));
    navigate(`/apis/${apiId}/edit`, { state: { row: r, index } });
  };

  // Helpers: normalize rows -> canonical model
  function rowsToCanonical(rows: RouteRow[], apiName = "MyAPI") {
    return {
      apiVersion: "v1",
      name: apiName,
      type: "REST",
      routes: rows.map((r) => ({
        path: r.resource,
        method: r.method,
        auth: normalizeAuth(r.auth),
        integration: {
          type: r.integration?.toLowerCase().includes("http")
            ? "http"
            : "lambda",
          url: "",
        },
      })),
    };
  }

  function normalizeAuth(a: string) {
    if (!a) return "API_KEY";
    const s = a.toUpperCase().replace(/\s+/g, "_");
    if (["API_KEY", "JWT", "NONE"].includes(s)) return s;
    return "API_KEY";
  }

  function canonicalToYAML(obj: any) {
    // lightweight JSON->YAML for simple structures (assumption)
    try {
      const json = JSON.stringify(obj, null, 2);
      // simple conversion: indent with 2 spaces, replace braces/brackets
      let yaml = json
        .replace(/\{\n/g, "")
        .replace(/\n\s*\}/g, "")
        .replace(/\"([^\"]+)\": /g, "$1: ")
        .replace(/\"([^\"]+)\"/g, "$1")
        .replace(/,\n/g, "\n")
        .replace(/\[\n/g, "")
        .replace(/\n\s*\]/g, "")
        .replace(/\n\s*\},/g, "\n");
      return yaml;
    } catch (e) {
      return "";
    }
  }

  function canonicalFromJSON(text: string) {
    try {
      const obj = JSON.parse(text);
      setCanonical(obj);
      setYamlText(canonicalToYAML(obj));
      return null;
    } catch (e: any) {
      return String(e.message ?? e);
    }
  }

  // basic validation rules from spec
  function validateCanonical(obj: any): string[] {
    const errs: string[] = [];
    if (!obj || typeof obj !== "object") {
      errs.push("config: must be an object");
      return errs;
    }
    if (!obj.apiVersion) errs.push("apiVersion: required");
    if (!obj.name) errs.push("name: required");
    if (!Array.isArray(obj.routes)) errs.push("routes: must be an array");
    else {
      const seen = new Set();
      obj.routes.forEach((r: any, i: number) => {
        if (!r.path) errs.push(`routes[${i}].path: required`);
        if (!r.method) errs.push(`routes[${i}].method: required`);
        const key = `${r.path}::${r.method}`;
        if (seen.has(key)) errs.push(`routes[${i}]: duplicate path+method`);
        seen.add(key);
        if (!r.auth) errs.push(`routes[${i}].auth: required`);
        else if (
          !["API_KEY", "JWT", "NONE"].includes(String(r.auth).toUpperCase())
        )
          errs.push(`routes[${i}].auth: invalid`);
        if (!r.integration || !r.integration.type)
          errs.push(`routes[${i}].integration: type required`);
      });
    }
    return errs;
  }

  // JSON editor change
  function onJsonChange(v: string) {
    setJsonText(v);
    const parseErr = canonicalFromJSON(v);
    if (parseErr) setValidationErrors([`JSON parse error: ${parseErr}`]);
  }

  // Apply terraform - lightweight preview
  function applyTerraform() {
    // parse resource names and show a pretend plan
    const lines = tfText.split("\n").map((l) => l.trim());
    const names = lines
      .filter((l) => l.startsWith("resource"))
      .map((l) => l.split(" ")[1] ?? l);
    setValidationErrors([]);
    setCanonical({
      apiVersion: "v1",
      name: names[0] ?? "tf-api",
      type: "REST",
      routes: [],
    });
    setJsonText(JSON.stringify(canonical, null, 2));
  }

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "220px 1fr",
        gap: 2,
        p: 2,
        bgcolor: "background.default",
        color: "text.primary",
      }}
    >
      <Box
        component="aside"
        sx={{
          bgcolor: "background.paper",
          p: 2,
          borderRight: "1px solid",
          borderColor: "divider",
        }}
      >
        <Typography variant="h6" gutterBottom>
          APIs
        </Typography>
        <Box component="nav">
          <Typography sx={{ fontWeight: 700, mb: 1 }}>MyAPI</Typography>
          <Typography
            component={RouterLink}
            to={`/apis/${id}/routes`}
            sx={{
              display: "block",
              color: "primary.main",
              textDecoration: "none",
              mb: 0.5,
            }}
          >
            Resources
          </Typography>
          <Typography sx={{ fontWeight: 700 }}>
            Methods ({SAMPLE.length})
          </Typography>
          <Typography>Settings</Typography>
        </Box>
      </Box>

      <Box
        component="main"
        sx={{
          bgcolor: "background.paper",
          p: 2,
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography variant="h5">Routes</Typography>
          <Box>
            <Button
              variant="contained"
              color="primary"
              onClick={handleCreate}
              sx={{ mr: 1 }}
            >
              Create Method
            </Button>
            <Button variant="outlined">Actions</Button>
          </Box>
        </Box>

        <Box sx={{ display: "flex", gap: 1, alignItems: "center", my: 2 }}>
          <Typography>API</Typography>
          <Select size="small" value={id || "MyAPI"} sx={{ minWidth: 120 }}>
            <MenuItem value="MyAPI">MyAPI</MenuItem>
          </Select>

          <Typography sx={{ ml: 2 }}>Show</Typography>
          <Select
            size="small"
            value={String(showCount)}
            onChange={(e) => setShowCount(Number(e.target.value))}
            sx={{ minWidth: 80 }}
          >
            <MenuItem value="10">10</MenuItem>
            <MenuItem value="25">25</MenuItem>
            <MenuItem value="50">50</MenuItem>
          </Select>

          <TextField
            placeholder="Search routes..."
            size="small"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            sx={{ ml: "auto", minWidth: 240, bgcolor: "background.default" }}
          />

          <Select
            size="small"
            value={configMode}
            onChange={(e) => setConfigMode(e.target.value as any)}
            sx={{ ml: 2 }}
          >
            <MenuItem value="resource">Resource Form</MenuItem>
            <MenuItem value="json">JSON / YAML</MenuItem>
            <MenuItem value="terraform">Terraform</MenuItem>
          </Select>

          <FormControlLabel
            control={
              <Checkbox
                checked={isGraphQL}
                onChange={(e) => setIsGraphQL(e.target.checked)}
              />
            }
            label="GraphQL"
            sx={{ ml: 1 }}
          />
        </Box>

        {isGraphQL ? (
          <Box>
            <Typography variant="subtitle1">GraphQL Schema (SDL)</Typography>
            <TextField
              fullWidth
              multiline
              minRows={6}
              value={jsonText}
              onChange={(e) => {
                setJsonText(e.target.value);
                const v = e.target.value;
                const errs: string[] = [];
                if (!/type\s+Query/.test(v))
                  errs.push("SDL: missing Query type");
                setValidationErrors(errs);
                if (errs.length === 0)
                  setCanonical({
                    apiVersion: "v1",
                    name: id || "graphql-api",
                    type: "GRAPHQL",
                    sdl: v,
                  });
              }}
              sx={{ mt: 1 }}
            />
          </Box>
        ) : (
          <>
            {configMode === "resource" && (
              <TableContainer sx={{ mt: 1 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Resource</TableCell>
                      <TableCell>Method</TableCell>
                      <TableCell>Auth</TableCell>
                      <TableCell>Integration</TableCell>
                      <TableCell>Caching</TableCell>
                      <TableCell>Rate Limit</TableCell>
                      <TableCell>Edit</TableCell>
                      <TableCell>Metrics</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rowsData !== null && rowsData.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8}>
                          <Typography>No APIs</Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      rows.map((r, i) => (
                        <TableRow key={i}>
                          <TableCell>{r.resource}</TableCell>
                          <TableCell>
                            <Chip
                              label={r.method}
                              color="primary"
                              size="small"
                            />
                          </TableCell>
                          <TableCell>{r.auth}</TableCell>
                          <TableCell>{r.integration}</TableCell>
                          <TableCell>Disabled</TableCell>
                          <TableCell>Disabled</TableCell>
                          <TableCell>
                            <Button
                              variant="text"
                              onClick={() => handleEdit(r, i)}
                              sx={{ color: "warning.main" }}
                            >
                              Edit
                            </Button>
                          </TableCell>
                          <TableCell>
                            <Button variant="contained">•••</Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {configMode === "json" && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="subtitle1">JSON / YAML Editor</Typography>
                <Box sx={{ display: "flex", gap: 2, mt: 1 }}>
                  <TextField
                    multiline
                    minRows={10}
                    value={jsonText}
                    onChange={(e) => onJsonChange(e.target.value)}
                    sx={{ flex: 1 }}
                  />
                  <TextField
                    multiline
                    minRows={10}
                    value={yamlText}
                    sx={{ flex: 1 }}
                    InputProps={{ readOnly: true }}
                  />
                </Box>
              </Box>
            )}

            {configMode === "terraform" && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="subtitle1">
                  Terraform Editor (preview)
                </Typography>
                <TextField
                  multiline
                  minRows={10}
                  value={tfText}
                  onChange={(e) => setTfText(e.target.value)}
                  sx={{ width: "100%", mt: 1 }}
                />
                <Box sx={{ mt: 1 }}>
                  <Button variant="contained" onClick={applyTerraform}>
                    Preview Plan
                  </Button>
                </Box>
              </Box>
            )}
          </>
        )}

        {validationErrors && validationErrors.length > 0 && (
          <Box sx={{ mt: 2, color: "error.main" }}>
            <Typography variant="subtitle2">Validation Errors:</Typography>
            <ul>
              {validationErrors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          </Box>
        )}

        <Box sx={{ mt: 2 }}>
          <Typography variant="body2">
            {rowsData === null
              ? error
                ? `Showing ${rows.length} (fallback) — ${error}`
                : `Loading... showing ${rows.length}`
              : `Showing 1 to ${rows.length} of ${rowsData.length} entries`}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
