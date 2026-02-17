import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Button,
  TextField,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  IconButton,
  Container,
} from "@mui/material";
import { Edit as EditIcon, Delete as DeleteIcon } from "@mui/icons-material";
import { listAPIs, deleteAPI, type APIItem } from "../services/apis";

export default function Routes() {
  const navigate = useNavigate();
  const [apis, setApis] = useState<APIItem[]>([]);
  const [filteredApis, setFilteredApis] = useState<APIItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  // Fetch APIs from server
  useEffect(() => {
    let mounted = true;

    (async () => {
      try {
        setLoading(true);
        const res = await listAPIs();
        if (!mounted) return;
        setApis(res);
        setFilteredApis(res);
      } catch (e: any) {
        if (!mounted) return;
        setError(e?.message ?? String(e));
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => {
      mounted = false;
    };
  }, []);

  // Filter APIs based on search
  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredApis(apis);
      return;
    }
    const term = searchTerm.toLowerCase();
    setFilteredApis(
      apis.filter(
        (api) =>
          api.name.toLowerCase().includes(term) ||
          api.description?.toLowerCase().includes(term),
      ),
    );
  }, [searchTerm, apis]);

  const handleCreate = () => {
    navigate(`/apis/create`);
  };

  const handleView = (api: APIItem) => {
    navigate(`/apis/${api.id}`);
  };

  const handleEdit = (api: APIItem) => {
    navigate(`/apis/${api.id}/edit`);
  };

  const handleDelete = async (api: APIItem) => {
    if (!window.confirm(`Are you sure you want to delete "${api.name}"?`)) {
      return;
    }
    try {
      await deleteAPI(api.id);
      setApis((prev) => prev.filter((a) => a.id !== api.id));
      setFilteredApis((prev) => prev.filter((a) => a.id !== api.id));
    } catch (e: any) {
      alert(e?.message ?? String(e));
    }
  };

  // Extract routes from config if available
  const getRoutesSummary = (api: APIItem) => {
    if (api.config && api.config.routes && Array.isArray(api.config.routes)) {
      return `${api.config.routes.length} routes`;
    }
    return "—";
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Typography variant="h4">APIs</Typography>
        <Button variant="contained" color="primary" onClick={handleCreate}>
          Create API
        </Button>
      </Box>

      <Box sx={{ mb: 2 }}>
        <TextField
          placeholder="Search APIs..."
          size="small"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          sx={{ minWidth: 300 }}
        />
      </Box>

      {loading ? (
        <Typography>Loading...</Typography>
      ) : error ? (
        <Typography color="error">Error: {error}</Typography>
      ) : (
        <TableContainer sx={{ bgcolor: "background.paper" }}>
          <Table>
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
              {filteredApis.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <Typography variant="h6" sx={{ py: 4 }}>
                      No APIs
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filteredApis.map((api) => (
                  <TableRow
                    key={api.id}
                    hover
                    onClick={() => handleView(api)}
                    sx={{ cursor: "pointer" }}
                  >
                    <TableCell>
                      {api.name}
                      {api.description && (
                        <Typography
                          variant="caption"
                          display="block"
                          color="text.secondary"
                        >
                          {api.description}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>{getRoutesSummary(api)}</TableCell>
                    <TableCell>API Key</TableCell>
                    <TableCell>HTTP Backend</TableCell>
                    <TableCell>Disabled</TableCell>
                    <TableCell>Disabled</TableCell>
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEdit(api);
                        }}
                        color="warning"
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(api);
                        }}
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outlined"
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleView(api);
                        }}
                      >
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Box sx={{ mt: 2 }}>
        <Typography variant="body2">
          Showing 1 to {filteredApis.length} of {apis.length} entries
        </Typography>
      </Box>
    </Container>
  );
}
