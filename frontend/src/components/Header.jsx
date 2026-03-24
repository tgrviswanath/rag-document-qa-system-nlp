import React from "react";
import { AppBar, Toolbar, Typography } from "@mui/material";
import QuestionAnswerIcon from "@mui/icons-material/QuestionAnswer";

export default function Header() {
  return (
    <AppBar position="static" color="primary">
      <Toolbar>
        <QuestionAnswerIcon sx={{ mr: 1 }} />
        <Typography variant="h6" fontWeight="bold">
          RAG Document QA System
        </Typography>
      </Toolbar>
    </AppBar>
  );
}
