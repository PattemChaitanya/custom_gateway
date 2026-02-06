import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { getAPI, type APIItem } from "../services/apis";
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
} from "@mui/material";

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

  const [apiData, setApiData] = useState<APIItem | null>(null);
  const [apiType, setApiType] = useState<string>("rest");
  const [routes, setRoutes] = useState<Route[]>([]);
  const [selectedRoute, setSelectedRoute] = useState<Route | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Testing state
  const [method, setMethod] = useState("POST");
  const [path, setPath] = useState("/register");
  const [body, setBody] = useState(
    '{\n  "email": "test@example.com",\n  "password": "mypassword"\n}',
  );
  const [response, setResponse] = useState<string>("");
  const [latency, setLatency] = useState<number | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  // Fetch API data
  useEffect(() => {
    if (!apiId) return;

    (async () => {
      try {
        setLoading(true);
        const data = await getAPI(apiId);
        setApiData(data);

        // Detect API type
        const detectedType =
          data.config?._meta?.ui?.type || data.type || "rest";
        setApiType(detectedType);

        // Extract routes from config
        if (
          data.config &&
          data.config.routes &&
          Array.isArray(data.config.routes)
        ) {
          const extractedRoutes = data.config.routes.map((r: any) => ({
            path: r.path || r.resource || "/",
            method: r.method || "GET",
            auth: r.auth || "API Key",
            integration: r.integration,
            requestBodyModel: r.requestBodyModel || r.schema,
            validation: r.validation,
          }));
          setRoutes(extractedRoutes);
          if (extractedRoutes.length > 0) {
            setSelectedRoute(extractedRoutes[0]);
            setPath(extractedRoutes[0].path);
            setMethod(extractedRoutes[0].method);
          }
        } else {
          // Create default route
          setRoutes([{ path: "/", method: "GET", auth: "API Key" }]);
          setSelectedRoute({ path: "/", method: "GET", auth: "API Key" });
        }
      } catch (e: any) {
        setError(e?.message ?? String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, [apiId]);

  async function handleTest() {
    setResponse("");
    setTestError(null);
    const start = performance.now();
    try {
      // Get integration URL from the selected route
      const integrationUrl =
        selectedRoute?.integration?.url || selectedRoute?.integration?.uri;

      if (!integrationUrl) {
        throw new Error("No integration URL configured for this route");
      }

      // Build full URL
      const fullUrl = integrationUrl.includes("://")
        ? integrationUrl
        : `${integrationUrl}${path}`;

      const requestData = body.trim() ? JSON.parse(body) : undefined;

      // Make direct request to integration URL
      const resp = await fetch(fullUrl, {
        method: method,
        headers: {
          "Content-Type": "application/json",
          ...(selectedRoute?.auth === "API_KEY" && { "x-api-key": "test-key" }),
        },
        body: requestData ? JSON.stringify(requestData) : undefined,
      });

      const end = performance.now();
      setLatency(Math.round(end - start));

      const responseData = await resp.text();
      try {
        const jsonData = JSON.parse(responseData);
        setResponse(JSON.stringify(jsonData, null, 2));
      } catch {
        setResponse(responseData);
      }

      if (!resp.ok) {
        setTestError(`HTTP ${resp.status}: ${resp.statusText}`);
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

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 2 }}>
        <Typography>Loading...</Typography>
      </Container>
    );
  }

  if (error || !apiData) {
    return (
      <Container maxWidth="lg" sx={{ py: 2 }}>
        <Alert severity="error">Error: {error || "API not found"}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
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
                            color={apiType === "rest" ? "primary" : "secondary"}
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
              <Paper sx={{ p: 2, bgcolor: "background.default" }} elevation={0}>
                <Typography variant="subtitle1" gutterBottom>
                  {apiType === "rest" ? "Method Request" : "Operation Details"}
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
              <Paper sx={{ p: 2, bgcolor: "background.default" }} elevation={0}>
                <Typography variant="subtitle1" gutterBottom>
                  {apiType === "rest"
                    ? "Request Validation"
                    : "Schema Validation"}
                </Typography>
                <Typography color="text.secondary">
                  {selectedRoute?.validation ||
                    (apiType === "rest" ? "Params Body: None" : "Schema: None")}
                </Typography>
              </Paper>

              {/* Logs */}
              <Paper sx={{ p: 2, bgcolor: "background.default" }} elevation={0}>
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
              Testing
            </Typography>

            {selectedRoute?.integration?.url && (
              <Alert severity="info" sx={{ mb: 1, fontSize: "0.75rem" }}>
                <Typography
                  variant="caption"
                  display="block"
                  sx={{ fontWeight: 600 }}
                >
                  Integration URL:
                </Typography>
                <Typography variant="caption" sx={{ wordBreak: "break-all" }}>
                  {selectedRoute.integration.url}
                </Typography>
              </Alert>
            )}

            <Box
              sx={{ display: "flex", flexDirection: "column", gap: 1.5, mt: 2 }}
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
                label={apiType === "rest" ? "Request Body" : "Query/Mutation"}
                multiline
                minRows={6}
                maxRows={10}
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
    </Container>
  );
}
