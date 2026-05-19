.PHONY: help test smoke

help:
	@echo "Khiip developer targets:"
	@echo ""
	@echo "  make test   Run hermetic pytest suite (default; CI required check)"
	@echo "  make smoke  Run live recall round-trip smoke (real network; NOT in CI)"
	@echo ""
	@echo "Smoke runs against an isolated KHIIP_HOME=\$$(mktemp -d) sandbox;"
	@echo "your real ~/.config/khiip + ~/.local/share/khiip + ~/khiip-vault are untouched."

test:
	pytest

smoke:
	bash _scripts/smoke/recall_roundtrip.sh
