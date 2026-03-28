# TODO — Phase 3: HydraDB Real Integration

## Plan
- [x] Read current hydra.py, config.py
- [x] Add `hydra_tenant_id` to config.py Settings
- [x] Rewrite `_hydra_*` methods in hydra.py to use real HydraDB API
- [x] Create hydra_knowledge.py utility for RAG knowledge upload
- [x] Verify all changes are consistent

## Notes
- Redis fallback kept intact
- Public API unchanged (create_session, append_turn, get_history, clear_session)
- Only _hydra_* private methods were modified
