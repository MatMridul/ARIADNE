import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import "@/design/globals.css";
import { AppShell } from "@/shell/AppShell";
import { CommandCenterPage } from "@/pages/CommandCenterPage";
import { ConnectPage } from "@/onboarding";
import { TopologyPage } from "@/pages/TopologyPage";
import { IncidentsPage } from "@/pages/IncidentsPage";
import { EvaluationPage } from "@/pages/EvaluationPage";
import { AuditPage } from "@/pages/AuditPage";

const queryClient = new QueryClient();

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <CommandCenterPage /> },
      { path: "connect", element: <ConnectPage /> },
      { path: "topology", element: <TopologyPage /> },
      { path: "incidents", element: <IncidentsPage /> },
      { path: "evaluation", element: <EvaluationPage /> },
      { path: "audit", element: <AuditPage /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>
);
