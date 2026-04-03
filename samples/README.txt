Sample files:
  ml_textbook_chapter.txt  - ~800 word ML textbook chapter (upload to RAG system)
  questions_for_rag.txt    - 10 questions to ask after uploading the document

Usage:
  1. Upload ml_textbook_chapter.txt to the RAG system
  2. Ask each question from questions_for_rag.txt one by one
  3. Verify answers are grounded in the document content

Expected answers (grounded in document):
  Q1: supervised, unsupervised, reinforcement learning
  Q2: supervised uses labelled data; unsupervised finds patterns without labels
  Q3: agent learns through trial and error with rewards/penalties
  Q4: overfitting = learning noise; prevented by regularisation, dropout, early stopping
  Q5: splits data into k folds, trains k times, averages performance
