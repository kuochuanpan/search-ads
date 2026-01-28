
import { useState, useEffect, ReactNode } from 'react';
import { api } from '@/lib/api';

interface StartupGuardProps {
    children: ReactNode;
}

export function StartupGuard({ children }: StartupGuardProps) {
    const [isReady, setIsReady] = useState(false);
    const [retryCount, setRetryCount] = useState(0);

    useEffect(() => {
        let mounted = true;
        let timeoutId: any;

        const checkHealth = async () => {
            try {
                // We use a simple fetch here to avoid circular dependencies or complex error handling in the early stage
                // Use the native fetch which will be routed through the API client's proxy logic if needed,
                // but since we are in the main process, we can rely on the api.ts helpers if they are robust.
                // Let's rely on api.ts as it handles the Tauri/Browser switching.
                await api.getStats(); // Any simple GET request to check connectivity
                if (mounted) {
                    setIsReady(true);
                }
            } catch (e) {
                console.log('Backend not ready, retrying...', e);
                if (mounted) {
                    setRetryCount(prev => prev + 1);
                    // Exponential backoff or constant polling? Constant is fine for startup.
                    timeoutId = setTimeout(checkHealth, 500);
                }
            }
        };

        checkHealth();

        return () => {
            mounted = false;
            clearTimeout(timeoutId);
        };
    }, []);

    if (isReady) {
        return <>{children}</>;
    }

    return (
        <div className="fixed inset-0 flex flex-col items-center justify-center bg-background text-foreground animate-in fade-in duration-500">
            <div className="flex flex-col items-center gap-6 p-8">
                <div className="relative">
                    <div className="w-16 h-16 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-8 h-8 bg-background rounded-full" />
                    </div>
                </div>

                <div className="text-center space-y-2">
                    <h1 className="text-2xl font-bold tracking-tight">Search-ADS</h1>
                    <p className="text-muted-foreground animate-pulse">
                        Initializing backend services...
                    </p>
                    {retryCount > 5 && (
                        <p className="text-xs text-muted-foreground/50">
                            Waiting for server request ({retryCount})...
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
