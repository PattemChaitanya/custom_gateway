import React from "react";
import {
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Grid,
  Paper,
  Box,
  Container,
  Stack,
} from "@mui/material";

export const TableSkeleton: React.FC<{ columns?: number; rows?: number }> = ({
  columns = 6,
  rows = 5,
}) => (
  <TableContainer>
    <Table>
      <TableHead>
        <TableRow>
          {Array.from({ length: columns }).map((_, i) => (
            <TableCell key={i}>
              <Skeleton variant="text" width="60%" />
            </TableCell>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {Array.from({ length: rows }).map((_, rowIdx) => (
          <TableRow key={rowIdx}>
            {Array.from({ length: columns }).map((_, colIdx) => (
              <TableCell key={colIdx}>
                <Skeleton variant="text" />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </TableContainer>
);

export const StatCardsSkeleton: React.FC<{ count?: number }> = ({
  count = 3,
}) => (
  <Grid container spacing={3} sx={{ mb: 3 }}>
    {Array.from({ length: count }).map((_, i) => (
      <Grid item xs={12} sm={4} key={i}>
        <Paper sx={{ p: 2 }}>
          <Skeleton variant="text" width="50%" height={28} />
          <Skeleton variant="text" width="30%" height={48} />
        </Paper>
      </Grid>
    ))}
  </Grid>
);

export const DetailPageSkeleton: React.FC = () => (
  <Container maxWidth="xl" sx={{ py: 2 }}>
    <Grid container spacing={2}>
      <Grid item xs={12} md={3}>
        <Paper sx={{ p: 2 }}>
          <Skeleton variant="text" width="60%" height={32} />
          <Skeleton variant="text" width="40%" sx={{ mb: 2 }} />
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton
              key={i}
              variant="rectangular"
              height={40}
              sx={{ mb: 1, borderRadius: 1 }}
            />
          ))}
        </Paper>
      </Grid>
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2 }}>
          <Skeleton variant="text" width="40%" height={32} sx={{ mb: 2 }} />
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton
              key={i}
              variant="rectangular"
              height={100}
              sx={{ mb: 2, borderRadius: 1 }}
            />
          ))}
        </Paper>
      </Grid>
      <Grid item xs={12} md={3}>
        <Paper sx={{ p: 2 }}>
          <Skeleton variant="text" width="60%" height={32} sx={{ mb: 2 }} />
          <Skeleton
            variant="rectangular"
            height={200}
            sx={{ borderRadius: 1 }}
          />
          <Skeleton
            variant="rectangular"
            height={40}
            sx={{ mt: 2, borderRadius: 1 }}
          />
        </Paper>
      </Grid>
    </Grid>
  </Container>
);
