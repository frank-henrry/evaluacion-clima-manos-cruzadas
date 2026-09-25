import { useVisitas } from '../../hooks/useVisitas.js';
import HistoricoView from './HistoricoView.jsx';

/**
 * CONTAINER: conecta `useVisitas` (estado + capa de datos) con la vista.
 * Un 401 llama a `onSessionExpired` (= `expireSession` de `useLogin`).
 */
export default function HistoricoContainer({ session, onSessionExpired }) {
  const state = useVisitas({
    token: session.token,
    onUnauthorized: onSessionExpired,
  });

  return (
    <HistoricoView
      filtros={state.filtros}
      orden={state.orden}
      direccion={state.direccion}
      data={state.data}
      error={state.error}
      isLoading={state.isLoading}
      onAplicarFiltros={state.aplicarFiltros}
      onLimpiar={state.limpiar}
      onOrdenar={state.ordenar}
      onCambiarPagina={state.irAPagina}
      onReintentar={state.reintentar}
    />
  );
}
