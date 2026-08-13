# Agente RAG — repo-ejemplo (caso GTI Orienta)

> Repo de **referencia** para la práctica del Asistente DNI de la asignatura
> *Inteligencia Artificial* (3º GTI, UPV). **Léelo como ejemplo de cómo
> entregar**, no como plantilla a forkear: el caso (GTI Orienta) es distinto
> al que vais a entregar (DNI Valencia).

## ¿Por qué este repo es un ejemplo y no la solución?

| Eje | Práctica oficial | Este repo |
|---|---|---|
| Caso | Asociación DNI Valencia | Orientación académica GTI |
| Corpus | 16 `.txt` (se os entrega) | 4 `.txt` (uno por curso del grado GTI) |
| Banda | Vosotros decidís hasta dónde llegáis | 5 + 6 + 7 implementadas, hexagonal **NO** |

El **patrón** (chunking, embeddings, retrieval, prompt anti-alucinación,
cita de fuentes, métricas) es el mismo. El **dominio** es distinto. Eso
permite que copiéis la **estructura** sin copiar la **solución**.

## Arranque en menos de 5 minutos

```bash
# 1. Clonar y entrar
git clone <este-repo>
cd agente-rag-gti

# 2. Instalar (Python 3.11+)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Tener Ollama corriendo y los dos modelos disponibles
#    (en local. Para probar contra UPV ver .env.example)
ollama pull gemma2:27b
ollama pull nomic-embed-text

# 4. Construir el índice (~ 30-90 s)
python scripts/build_index.py

# 5. Lanzar una consulta
python consultar.py "¿Hay una asignatura sobre videojuegos en GTI?"
```

Salida (resumida):

```json
{
  "respuesta": "Sí. En 4º se imparte 'Desarrollo de Videojuegos' (4_cuarto.txt)...",
  "fuentes": ["4_cuarto.txt", "3_tercero.txt"],
  "chunks": [...],
  "metricas": {"prompt_tokens": 612, "output_tokens": 45, "tokens_per_sec": 38.2, "latencia_s": 1.7, "modelo": "gemma2:27b"}
}
```

## Estructura del repositorio

```
agente-rag-gti/
├── consultar.py          # CONTRATO §9 opción A (módulo Python)
├── api.py                # CONTRATO §9 opción B (POST /query con FastAPI)
├── features.json         # Declaración para el corrector — SIN ESTO LA NOTA ES 0
├── GRUPO.md              # Plantilla equipo
├── AI_USAGE.md           # Plantilla declaración de uso de IA
├── corpus/               # 4 .txt (1º a 4º curso de GTI)
├── src/agente_rag/       # Pipeline RAG modular (chunker, retriever, generator, ...)
├── scripts/
│   ├── build_index.py    # Construye índice ChromaDB persistente
│   └── run_eval.py       # Ejecuta el benchmark
├── tests/                # pytest sin dependencia de red (mocks de Ollama)
├── benchmark/
│   ├── preguntas.json    # 8 preguntas tipo (incluye 2 fuera-de-ámbito)
│   └── README.md         # Cómo evaluar resultados
├── docs/
│   ├── ARCHITECTURE.md   # Decisiones de diseño y por qué
│   └── CONTRACT.md       # Contrato de interfaz al detalle
└── .github/workflows/ci.yml   # Tests + lint en cada push
```

## Bandas implementadas

- **Banda 5** ✓ — pipeline RAG con prompt anti-alucinación.
- **Banda 6** ✓ — cada respuesta cita el archivo fuente.
- **Banda 7** parcial — el contrato emite `chunks` y `metricas` (tokens,
  tokens/s, latencia). **Falta** el benchmark con 4 modelos: lo dejamos a
  los alumnos para que midan tradeoffs reales.
- **Banda 8** — no implementada. Sería integrar RAGAs sobre los outputs
  de `scripts/run_eval.py`.
- **Banda 10** — *deliberadamente no implementada*. El reto del 10 es
  refactorizar este single-agent a hexagonal (ver `manual_desarrollador_dni.pdf`
  sección 4). Si os lo damos hecho, regalamos la nota máxima.

## Tests

```bash
pytest -q
```

Los tests **no llaman a Ollama**: parchean `retrieve` y `generate` con stubs
para verificar que el contrato (`{respuesta, fuentes, chunks, metricas, trazas}`)
se respeta y que el `features.json` declara coherentemente lo que entrega.

## Por qué este repo está bien estructurado (lo que queremos que copiéis)

1. **Separación clara `src/` ↔ `consultar.py`/`api.py`**. La lógica vive en
   el paquete, los puntos de entrada son finos. Si mañana queremos meter
   un Streamlit (extra +1.5), es otro fichero más, no un refactor.
2. **`features.json` válido y honesto**. Marca `true` solo lo que
   funciona. Los alumnos que declaren `banda7=true` sin `benchmark/` se
   detectan en el corrector.
3. **Tests aislados de red**. CI corre en GitHub Actions sin Ollama.
4. **Conventional commits granulares**. Mira `git log --oneline`: cada
   commit toca una capa, no hay un commit-monstruo "lo subo todo".
5. **Cita de fuentes literal en el prompt** (`prompts.py`). La banda 6 se
   gana en el prompt, no en el postproceso.

## Avisos legales y éticos

- Modelo y corpus son material docente. No lo redistribuyáis fuera del aula
  sin autorización del profesor.
- Si añadís `boto3`/AWS Rekognition, **rotad credenciales** después.
  Ningún `.env` con secretos debe llegar a un repo público.

## Créditos

Vicente Rivas Monferrer & Juan M. Alberola — Universitat Politècnica de
València, 2026.
