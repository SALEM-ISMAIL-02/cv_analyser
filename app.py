import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from models.llm_extractor import CvExtractor, OllamaConnectionError, OllamaModelNotFoundError
from schemas.cv_schema import CvDocument
from utils.file_extractor import extract_text_from_pdf
from utils.text_hints import extract_hints

app = FastAPI(
    title="CV Analyser",
    description=(
        "Extract structured career data from text-based PDF CVs into "
        "[FreeCV cv.json v1.2](https://freecv.org/schema/cv/v1.json) format. "
        "Requires a local [Ollama](https://ollama.com) instance."
    ),
    version="1.0.0",
)

extractor = CvExtractor(model_name=os.getenv("OLLAMA_MODEL", "llama3.2:3b-gpu"))


@app.on_event("startup")
def warmup_model():
    try:
        extractor.warmup()
    except Exception:
        pass


@app.get("/health", tags=["System"])
def health():
    """Check Ollama connectivity and whether the configured model is available."""
    return extractor.health_check()


@app.post(
    "/extract",
    response_model=CvDocument,
    tags=["CV"],
    summary="Extract CV from PDF",
    response_description="Structured cv.json document (FreeCV v1.2)",
)
async def extract_cv(file: UploadFile = File(..., description="Text-based PDF resume")):
    """
    Upload a PDF resume and receive structured JSON matching the FreeCV cv.json schema.

    **Requirements**
    - PDF must contain selectable text (not a scanned image)
    - Ollama with `llama3.2:3b-gpu` (fits GTX 1650 4GB on GPU)

  **Setup:** `.\\scripts\\setup_ollama_gpu.ps1` then `.\\scripts\\start.ps1`
    Never set `OLLAMA_NUM_GPU=0` — that forces CPU-only.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        text = extract_text_from_pdf(file.file)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read PDF: {exc}") from exc

    hints = extract_hints(text)

    health = extractor.health_check()
    if health.get("status") == "model_missing":
        raise HTTPException(
            status_code=503,
            detail=(
                f"Model '{health.get('configured_model')}' not installed. "
                "Run: .\\scripts\\setup_ollama_gpu.ps1  "
                f"(installed: {health.get('available_models', [])})"
            ),
        )

    try:
        cv = extractor.process_cv(text, hints=hints)
    except OllamaConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OllamaModelNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {exc}") from exc

    return cv
