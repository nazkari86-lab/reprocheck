# Contributing to Thread-RAG

Thank you for interest in contributing to Thread-RAG!

## Code Standards

### Style
- Follow PEP 8
- Use type hints throughout
- Maximum line length: 100 characters
- Docstrings for all functions and classes

### Testing
- All new features must include tests
- Run `eval_validator.py` to validate data integrity
- Test with multiple models before submitting

### Documentation
- Update README.md for user-facing changes
- Update AGENTS.md for architecture changes
- Include examples for new features

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Add tests if applicable
5. Run validation: `python eval_validator.py`
6. Commit with clear messages
7. Push to your fork
8. Open a pull request

## Areas for Contribution

### High Priority
- Additional retrieval strategies (e.g., ColBERT, DPR)
- More evaluation metrics (e.g., BLEU, ROUGE)
- GPU acceleration for embeddings
- Distributed evaluation support

### Medium Priority
- Multi-language support
- Alternative vector stores (Weaviate, Qdrant)
- Performance optimizations
- Additional LLM integrations

### Low Priority
- UI improvements
- Documentation enhancements
- Code refactoring

## Reporting Issues

When reporting issues, include:
- Exact error message
- Steps to reproduce
- Model versions being used
- Relevant configuration settings
- Expected vs actual behavior

## Questions?

- Check `AGENTS.md` for architecture details
- Review `EVAL_COMPLETE_GUIDE.md` for evaluation setup
- Look at `eval_config.py` for configuration options

---

We look forward to your contributions!

