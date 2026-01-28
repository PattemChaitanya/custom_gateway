import { Link as RouterLink } from 'react-router-dom';
import type { APIItem } from '../services/apis';
import Paper from '@mui/material/Paper';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import ListItemSecondaryAction from '@mui/material/ListItemSecondaryAction';
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

type Props = {
  items: APIItem[];
  onDelete: (id: number) => void;
};

export default function ApiList({ items, onDelete }: Props) {
  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>APIs</Typography>
      <List>
        {items.map((a) => (
          <ListItem key={a.id} divider>
            <ListItemText
              primary={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <RouterLink to={`/apis/${a.id}`} style={{ fontWeight: 700, color: 'inherit', textDecoration: 'none' }}>{a.name}</RouterLink>
                  <Typography variant="body2" color="text.secondary">({a.version})</Typography>
                </Box>
              }
              secondary={a.description || '—'}
            />

            <ListItemSecondaryAction>
              <IconButton edge="end" size="small" component={RouterLink} to={`/apis/${a.id}/edit`} aria-label="edit">
                <EditIcon fontSize="small" />
              </IconButton>
              <IconButton edge="end" size="small" onClick={() => onDelete(a.id)} aria-label="delete" sx={{ ml: 1 }}>
                <DeleteIcon fontSize="small" />
              </IconButton>
            </ListItemSecondaryAction>
          </ListItem>
        ))}
      </List>
    </Paper>
  );
}
