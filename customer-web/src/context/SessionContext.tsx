import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { resolveQrToken, getSession, setSessionToken, clearSessionToken, getSessionToken, HmsApiError } from '../api';
import type { CustomerSession } from '../types';

interface SessionContextType {
  sessionToken: string | null;
  session: CustomerSession | null;
  tableDisplayName: string;
  tableNumber: number | null;
  tableId: string | null;
  tableSessionId: string | null;
  currentOutstanding: string;
  customLimit: string;
  isLoading: boolean;
  error: string | null;
  initFromQr: (qrToken: string) => Promise<boolean>;
  refreshSession: () => Promise<void>;
  updateOutstanding: (amount: string) => void;
  updateLimit: (limit: string) => void;
  clearSession: () => void;
  startDemoSession: () => void;
}

const SessionContext = createContext<SessionContextType | null>(null);

export const SessionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sessionTokenState, setSessionTokenState] = useState<string | null>(getSessionToken());
  const [session, setSession] = useState<CustomerSession | null>(null);
  const [tableDisplayName, setTableDisplayName] = useState<string>(
    sessionStorage.getItem('hms_table_name') || ''
  );
  const [tableNumber, setTableNumber] = useState<number | null>(
    sessionStorage.getItem('hms_table_number') ? parseInt(sessionStorage.getItem('hms_table_number')!, 10) : null
  );
  const [tableId, setTableId] = useState<string | null>(
    sessionStorage.getItem('hms_table_id') || null
  );
  const [tableSessionId, setTableSessionId] = useState<string | null>(
    sessionStorage.getItem('hms_table_session_id') || null
  );
  const [currentOutstanding, setCurrentOutstanding] = useState<string>('0.00');
  const [customLimit, setCustomLimit] = useState<string>('5000.00');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const updateLimit = useCallback((limit: string) => {
    setCustomLimit(limit);
  }, []);

  const refreshSession = useCallback(async () => {
    const token = getSessionToken();
    if (!token) return;
    try {
      const sess = await getSession();
      setSession(sess);
      setTableDisplayName(sess.table_display_name);
      setTableNumber(sess.table_number);
      setTableId(sess.table_id);
      sessionStorage.setItem('hms_table_name', sess.table_display_name);
      sessionStorage.setItem('hms_table_number', sess.table_number.toString());
      sessionStorage.setItem('hms_table_id', sess.table_id);
    } catch (err) {
      if (err instanceof HmsApiError && (err.httpStatus === 401 || err.httpStatus === 403)) {
        clearSession();
      }
    }
  }, []);

  const initFromQr = useCallback(async (qrToken: string): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await resolveQrToken(qrToken);
      setSessionToken(res.session_token);
      setSessionTokenState(res.session_token);
      setTableDisplayName(res.table_display_name);
      setTableNumber(res.table_number);
      setTableId(res.table_id);
      setTableSessionId(res.session_id);

      sessionStorage.setItem('hms_table_name', res.table_display_name);
      sessionStorage.setItem('hms_table_number', res.table_number.toString());
      sessionStorage.setItem('hms_table_id', res.table_id);
      if (res.session_id) {
        sessionStorage.setItem('hms_table_session_id', res.session_id);
      }

      setIsLoading(false);
      return true;
    } catch (err: unknown) {
      setIsLoading(false);
      if (err instanceof HmsApiError) {
        setError(err.message || 'QR code is invalid or has expired.');
      } else {
        setError('Network error resolving QR code. Please check connection.');
      }
      return false;
    }
  }, []);

  const startDemoSession = useCallback(() => {
    const demoToken = 'demo-token-table-4';
    setSessionToken(demoToken);
    setSessionTokenState(demoToken);
    setTableDisplayName('Table 4 (Window Side)');
    setTableNumber(4);
    setTableId('table-demo-4');
    setTableSessionId('demo-session-4');
    sessionStorage.setItem('hms_table_name', 'Table 4 (Window Side)');
    sessionStorage.setItem('hms_table_number', '4');
    sessionStorage.setItem('hms_table_id', 'table-demo-4');
    sessionStorage.setItem('hms_table_session_id', 'demo-session-4');
    setError(null);
  }, []);

  const clearSession = useCallback(() => {
    clearSessionToken();
    setSessionTokenState(null);
    setSession(null);
    setTableDisplayName('');
    setTableNumber(null);
    setTableId(null);
    setTableSessionId(null);
    setCurrentOutstanding('0.00');
    sessionStorage.removeItem('hms_table_name');
    sessionStorage.removeItem('hms_table_number');
    sessionStorage.removeItem('hms_table_id');
    sessionStorage.removeItem('hms_table_session_id');
    sessionStorage.removeItem('hms_demo_orders');
  }, []);

  const updateOutstanding = useCallback((amount: string) => {
    setCurrentOutstanding(amount);
  }, []);

  useEffect(() => {
    if (sessionTokenState && !session) {
      refreshSession();
    }
  }, [sessionTokenState, session, refreshSession]);

  return (
    <SessionContext.Provider
      value={{
        sessionToken: sessionTokenState,
        session,
        tableDisplayName,
        tableNumber,
        tableId,
        tableSessionId,
        currentOutstanding,
        customLimit,
        isLoading,
        error,
        initFromQr,
        refreshSession,
        updateOutstanding,
        updateLimit,
        clearSession,
        startDemoSession,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
};

export const useSession = (): SessionContextType => {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used within SessionProvider');
  return ctx;
};
