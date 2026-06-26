import { useEffect, useRef } from 'react';
import LegacyApp from './App.js';

function App() {
    const appRef = useRef(null);

    useEffect(() => {
        const appNode = appRef.current;
        if (!appNode) return;

        const legacyApp = new LegacyApp();
        legacyApp.bootstrap();
    }, []);

    return <div id="app" ref={appRef} />;
}

export default App;
