import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { ConfirmProvider } from "./components/common/Confirm";
import { AccountProvider } from "./lib/account";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AccountProvider>
      <ConfirmProvider>
        <App />
      </ConfirmProvider>
    </AccountProvider>
  </React.StrictMode>
);
