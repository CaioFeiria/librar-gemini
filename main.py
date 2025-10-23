import os
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from dotenv import load_dotenv

# ====== Config ======
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL_NAME = "models/gemini-flash-latest"  # Ou "models/gemini-2.5-flash"

app = FastAPI(title="Validador LIBRAS")


# ====== Endpoint Único ======
@app.post("/validate-libras")
async def validate_libras(
        letter: str = Form(..., description="A letra que o aluno está tentando executar (ex: 'A')"),
        photo: UploadFile = File(..., description="Foto do aluno executando o sinal em LIBRAS"),
        reference_pdf: UploadFile = File(..., description="PDF com o alfabeto de referência em LIBRAS")
):
    try:
        if reference_pdf.content_type != "application/pdf":
            raise HTTPException(status_code=415, detail="O arquivo de referência deve ser um PDF.")
        if not photo.content_type.startswith("image/"):
            raise HTTPException(status_code=415, detail="A foto deve ser uma imagem (jpg, png, etc).")

        # ---- Ler os bytes dos arquivos ----
        photo_bytes = await photo.read()
        pdf_bytes = await reference_pdf.read()

        # ---- Preparar os "Parts" para o modelo ----
        photo_part = {
            "mime_type": photo.content_type,
            "data": photo_bytes
        }

        pdf_part = {
            "mime_type": reference_pdf.content_type,
            "data": pdf_bytes
        }

        # ---- PROMPT OTIMIZADO ----
        system_prompt = (
            f"Avaliador LIBRAS. Aluno tenta a letra '{letter}'. "
            f"Compare a foto (aluno) com a letra '{letter}' no PDF (referência). "
            "Responda em português. "
            "Inicie com 'Sim, está correto.' ou 'Não, está incorreto.' e justifique em uma única frase curta."
        )

        model = genai.GenerativeModel(
            MODEL_NAME,
            generation_config=GenerationConfig(
                temperature=0.2,
                max_output_tokens=512,  # 512 é um bom limite para uma resposta curta
            ),
            system_instruction=system_prompt
        )

        # Enviar os "parts" dos arquivos
        # O system_prompt já contém toda a instrução
        response = model.generate_content(
            [pdf_part, photo_part]
        )

        # verificação
        try:
            result_text = response.text
            return JSONResponse(content={"resultado": result_text})

        except Exception as e:
            finish_reason = "DESCONHECIDO"
            if response.candidates:
                finish_reason = response.candidates[0].finish_reason.name

            error_detail = (
                f"A resposta do modelo foi bloqueada ou retornou vazia. "
                f"Motivo (Finish Reason): {finish_reason}. "
                f"Erro original: {str(e)}"
            )
            return JSONResponse(status_code=500, content={"erro": error_detail})

    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"erro": he.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})