import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SessionProvider } from "./auth/Session";
import { App } from "./app/App";
import "@fontsource-variable/archivo/index.css";
import "./i18n";
import "./design/styles.css";
const client = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 20_000 } },
});
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <SessionProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </SessionProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
