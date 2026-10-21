import React, { useCallback, useState } from 'react';
import { SessionProvider, useSession } from './context/SessionContext';
import { CartProvider } from './context/CartContext';
import { HeaderBar } from './components/HeaderBar';
import { QrLandingPage } from './pages/QrLandingPage';
import { MenuPage } from './pages/MenuPage';
import { OrdersPage } from './pages/OrdersPage';
import { SessionErrorPage } from './pages/SessionErrorPage';
import { extractQrToken } from './utils/qrToken';

const AppContent: React.FC = () => {
  const { sessionToken, isLoading, error } = useSession();
  const [activeTab, setActiveTab] = useState<'menu' | 'orders'>('menu');
  const [isQrFlow, setIsQrFlow] = useState<boolean>(() => {
    // Check if URL has a QR token in any supported shape
    return extractQrToken() !== null;
  });

  const handleQrSuccess = useCallback(() => {
    setIsQrFlow(false);
    setActiveTab('menu');
  }, []);
  const handleQrError = useCallback((_msg: string) => {
    // the landing page shows the error and a "Try again" button
  }, []);

  if (isQrFlow) {
    return <QrLandingPage onSuccess={handleQrSuccess} onError={handleQrError} />;
  }

  if (!sessionToken && !isLoading) {
    // Not in QR flow and no session token
    return error ? (
      <SessionErrorPage message={error} />
    ) : (
      <SessionErrorPage message="Please scan your dining table's QR code to view the menu and place orders." />
    );
  }

  return (
    <div
      className="min-h-screen flex flex-col font-sans"
      style={{ background: 'var(--cream, #FFF8ED)' }}
    >
      <HeaderBar
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
      />

      <main className="flex-1">
        {activeTab === 'menu' ? (
          <MenuPage onOrderSuccess={() => setActiveTab('orders')} />
        ) : (
          <OrdersPage onBackToMenu={() => setActiveTab('menu')} />
        )}
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <CartProvider>
      <SessionProvider>
        <AppContent />
      </SessionProvider>
    </CartProvider>
  );
};

export default App;
