import React from "react";
import { Container } from "@mui/material";
import Header from "./components/Header";
import QAPage from "./pages/QAPage";

export default function App() {
  return (
    <>
      <Header />
      <Container maxWidth="md" sx={{ py: 4 }}>
        <QAPage />
      </Container>
    </>
  );
}
