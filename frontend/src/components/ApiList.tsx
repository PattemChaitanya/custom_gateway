import { Link } from 'react-router-dom';
import type { APIItem } from '../services/apis';

type Props = {
  items: APIItem[];
  onDelete: (id: number) => void;
};

export default function ApiList({ items, onDelete }: Props) {
  return (
    <div>
      <h3>APIs</h3>
      <ul>
        {items.map((a) => (
          <li key={a.id} style={{ marginBottom: 8 }}>
            <Link to={`/apis/${a.id}`} style={{ fontWeight: 700, marginRight: 8 }}>{a.name}</Link>
            <small>({a.version})</small> - {a.description || '—'}
            <Link to={`/apis/${a.id}/edit`}><button style={{ marginLeft: 8 }}>Edit</button></Link>
            <button style={{ marginLeft: 8 }} onClick={() => onDelete(a.id)}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
