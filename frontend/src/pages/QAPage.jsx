import React, { useState, useEffect, useRef } from "react";
import {
  Box, Button, CircularProgress, Alert, Typography, Paper, Chip,
  TextField, IconButton, Tooltip, Divider, List, ListItem,
  ListItemText, Collapse,
} from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import DeleteIcon from "@mui/icons-material/Delete";
import SendIcon from "@mui/icons-material/Send";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import { ingestDoc, askQuestion, getStats, clearDocs } from "../services/ragApi";

export default function QAPage() {
  const [stats, setStats] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState("");
  const [expandedSources, setExpandedSources] = useState({});
  const fileRef = useRef();
  const bottomRef = useRef();

  const fetchStats = async () => {
    try { const r = await getStats(); setStats(r.data); } catch (_) {}
  };

  useEffect(() => { fetchStats(); }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const handleUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await ingestDoc(fd);
      setMessages((prev) => [...prev, {
        role: "system",
        text: `✅ "${file.name}" ingested — ${r.data.chunks_added} chunks added.`,
      }]);
      await fetchStats();
    } catch (e) {
      setError(e.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const handleAsk = async () => {
    if (!question.trim()) return;
    const q = question.trim();
    setQuestion("");
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setAsking(true);
    setError("");
    try {
      const r = await askQuestion(q);
      setMessages((prev) => [...prev, {
        role: "assistant",
        text: r.data.answer,
        sources: r.data.sources,
      }]);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to get answer.");
    } finally {
      setAsking(false);
    }
  };

  const handleClear = async () => {
    await clearDocs();
    setMessages([]);
    setStats(null);
    await fetchStats();
  };

  const toggleSources = (idx) =>
    setExpandedSources((prev) => ({ ...prev, [idx]: !prev[idx] }));

  return (
    <Box>
      {/* Stats bar */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Chip
          label={`📚 ${stats?.total_docs ?? 0} docs  |  ${stats?.total_chunks ?? 0} chunks`}
          color={stats?.ready ? "success" : "default"}
        />
        <Chip label={`🤖 ${stats?.llm_model ?? "—"}`} variant="outlined" size="small" />
        <Chip label={`🔍 ${stats?.embed_model ?? "—"}`} variant="outlined" size="small" />
        <Tooltip title="Clear all documents">
          <IconButton size="small" onClick={handleClear} color="error">
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Drop zone */}
      <Paper
        variant="outlined"
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => fileRef.current.click()}
        sx={{
          p: 3, mb: 2, textAlign: "center", cursor: "pointer", borderStyle: "dashed",
          "&:hover": { bgcolor: "action.hover" },
        }}
      >
        <input ref={fileRef} type="file" hidden accept=".pdf,.docx,.doc,.txt"
          onChange={(e) => handleUpload(e.target.files[0])} />
        {uploading
          ? <CircularProgress size={24} />
          : <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 1 }}>
              <UploadFileIcon color="action" />
              <Typography color="text.secondary">
                Drag & drop or click to upload PDF / DOCX / TXT
              </Typography>
            </Box>
        }
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Chat messages */}
      <Paper variant="outlined" sx={{ minHeight: 300, maxHeight: 450, overflow: "auto", p: 2, mb: 2 }}>
        {messages.length === 0 && (
          <Typography color="text.secondary" textAlign="center" mt={4}>
            Upload a document, then ask questions about it.
          </Typography>
        )}
        {messages.map((msg, idx) => (
          <Box key={idx} sx={{ mb: 2 }}>
            {msg.role === "user" && (
              <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
                <Paper sx={{ p: 1.5, bgcolor: "primary.main", color: "white", maxWidth: "75%", borderRadius: 2 }}>
                  <Typography variant="body2">{msg.text}</Typography>
                </Paper>
              </Box>
            )}
            {msg.role === "assistant" && (
              <Box>
                <Paper variant="outlined" sx={{ p: 1.5, maxWidth: "85%", borderRadius: 2 }}>
                  <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>{msg.text}</Typography>
                  {msg.sources?.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      <Button size="small" onClick={() => toggleSources(idx)}
                        endIcon={expandedSources[idx] ? <ExpandLessIcon /> : <ExpandMoreIcon />}>
                        {msg.sources.length} source{msg.sources.length > 1 ? "s" : ""}
                      </Button>
                      <Collapse in={!!expandedSources[idx]}>
                        <List dense disablePadding>
                          {msg.sources.map((s, si) => (
                            <ListItem key={si} disablePadding sx={{ pl: 1 }}>
                              <ListItemText
                                primary={<Chip label={`${s.source} · chunk ${s.chunk}`} size="small" />}
                                secondary={<Typography variant="caption" color="text.secondary">
                                  {s.excerpt}…
                                </Typography>}
                              />
                            </ListItem>
                          ))}
                        </List>
                      </Collapse>
                    </Box>
                  )}
                </Paper>
              </Box>
            )}
            {msg.role === "system" && (
              <Typography variant="caption" color="success.main">{msg.text}</Typography>
            )}
          </Box>
        ))}
        {asking && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <CircularProgress size={16} />
            <Typography variant="caption" color="text.secondary">Thinking…</Typography>
          </Box>
        )}
        <div ref={bottomRef} />
      </Paper>

      <Divider sx={{ mb: 2 }} />

      {/* Question input */}
      <Box sx={{ display: "flex", gap: 1 }}>
        <TextField
          fullWidth size="small"
          placeholder="Ask a question about your documents…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleAsk()}
          disabled={asking || !stats?.ready}
        />
        <Button variant="contained" onClick={handleAsk}
          disabled={!question.trim() || asking || !stats?.ready}
          endIcon={asking ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}>
          Ask
        </Button>
      </Box>
      {!stats?.ready && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
          Upload at least one document to enable Q&A.
        </Typography>
      )}
    </Box>
  );
}
