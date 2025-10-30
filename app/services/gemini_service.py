import google.generativeai as genai
from google.generativeai.types import GenerationConfig

def configure_gemini(api_key: str):
    genai.configure(api_key=api_key)

def evaluate_letter(model_name: str, letter: str, photo_mime: str, photo_bytes: bytes,
                    pdf_mime: str, pdf_bytes: bytes) -> tuple[str | None, str | None]:
    """
    Retorna (result_text, finish_reason). Se bloqueado, result_text pode ser None.
    """
    system_prompt = (
        f"Avaliador LIBRAS. Aluno tenta a letra '{letter}'. "
        f"Compare a foto (aluno) com a letra '{letter}' no PDF (referência). "
        "Responda em português. "
        "Inicie com 'Sim, está correto.' ou 'Não, está incorreto.' e justifique em uma única frase curta."
    )

    model = genai.GenerativeModel(
        model_name,
        generation_config=GenerationConfig(temperature=0.2, max_output_tokens=512),
        system_instruction=system_prompt
    )

    response = model.generate_content([
        {"mime_type": pdf_mime, "data": pdf_bytes},
        {"mime_type": photo_mime, "data": photo_bytes},
    ])

    result_text, finish_reason = None, None
    try:
        result_text = response.text
    except Exception:
        pass

    try:
        if getattr(response, "candidates", None):
            finish_reason = response.candidates[0].finish_reason.name
    except Exception:
        pass

    return result_text, finish_reason
