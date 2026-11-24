"""SOC Copilot: investigação de logs com evidências rastreáveis."""

__version__ = "0.1.0"

# O runtime C++ do ambiente virtual evita carregar versões antigas do System32.
# Precisa acontecer antes de importar Chroma/NumPy/PyTorch.
from soc_copilot.windows_runtime import prepare_runtime

prepare_runtime()
