import os

# O mem0 liga telemetria (PostHog) por padrão e lê a flag no import do pacote.
# Este __init__ roda antes de engine.py importar o mem0, então o default aqui
# vale; quem quiser a telemetria ligada define MEM0_TELEMETRY=True no ambiente.
os.environ.setdefault("MEM0_TELEMETRY", "False")
