import React, { useState, useEffect } from 'react';
import { SessionProvider, useSession } from './context/SessionContext';
import { CartProvider } from './context/CartContext';
import { HeaderBar } from './components/HeaderBar';
import { QrLandingPage } from './pages/QrLandingPage';
import { MenuPage } from './pages/MenuPage';
import { OrdersPage } from './pages/OrdersPage';
import { SessionErrorPage } from './pages/SessionErrorPage';

const AppContent: React.FC = () => {
  const { sessionToken, isLoading, error } = useSession();
  const [activeTab, setActiveTab] = useState<'menu' | 'orders'>('menu');
  const [isQrFlow, setIsQrFlow] = useState<boolean>(() => {
    // Check if URL has QR parameters
    const pathMatches = window.location.pathname.match(/\/q\/([^/?#]+)/);
    const urlParams = new URLSearchParams(window.location.search);
    const hasQuery = urlParams.has('qr') || urlParams.has('token');
    const hasHash = window.location.hash.includes('/q/');
    return Boolean(pathMatches || hasQuery || hasHash);
  });

  useEffect(() => {
    // If we have a session token already, and not on a QR link, default to normal app
    if (sessionToken && !isQrFlow) {
      // ready
    }
  }, [sessionToken, isQrFlow]);

  if (isQrFlow) {
    return (
      <QrLandingPage
        onSuccess={() => {
          setIsQrFlow(false);
          setActiveTab('menu');
        }}
        onError={(_msg) => {
          // let landing page display error
        }}
      />
    );
  }

  if (!sessionToken && !isLoading) {
    // Not in QR flow and no session token
    return <SessionErrorPage message="Please scan your dining table's QR code to view the menu and place orders." />;
  }

  if (error && !sessionToken) {
    return <SessionErrorPage message={error} />;
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
    <SessionProvider>
      <CartProvider>
        <AppContent />
      </CartProvider>
    </SessionProvider>
  );
};

export default App;
