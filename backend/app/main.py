from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.v1.ticket_routes  import router as ticket_router
from app.v1.runbook_routes import router as runbook_router
<<<<<<< HEAD
from app.v1.rca_routes     import router as rca_router
=======
>>>>>>> d0486dcc903ac38b1d8a01d690a0881436a94549

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ GLOBAL ERROR HANDLER
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print("🔥 ERROR:", exc)
    return JSONResponse(
        status_code=500,
        content={"message": str(exc)},
    )

app.include_router(ticket_router,  prefix="/api")
<<<<<<< HEAD
app.include_router(runbook_router, prefix="/api")
app.include_router(rca_router,     prefix="/api")   
=======
app.include_router(runbook_router, prefix="/api")
>>>>>>> d0486dcc903ac38b1d8a01d690a0881436a94549
