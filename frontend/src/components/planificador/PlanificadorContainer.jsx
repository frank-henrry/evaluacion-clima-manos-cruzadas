import { usePrediccion } from '../../hooks/usePrediccion.js';
import PlanificadorView from './PlanificadorView.jsx';

/**
 * CONTAINER: conecta `usePrediccion` (estado + capa de datos) con la vista.
 * Un 401 llama a `onSessionExpired` (= `expireSession` de `useLogin`).
 */
export default function PlanificadorContainer({ session, onSessionExpired }) {
  const state = usePrediccion({
    token: session.token,
    onUnauthorized: onSessionExpired,
  });

  return (
    <PlanificadorView
      fecha={state.fecha}
      prediccion={state.prediccion}
      error={state.error}
      isLoading={state.isLoading}
      onFechaChange={state.selectFecha}
      onPredecir={state.predecir}
    />
  );
}
